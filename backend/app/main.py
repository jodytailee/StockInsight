from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.schemas.symbol import NewsItemOut, PricePointOut, SymbolCreate, SymbolOut
from app.services.news_service import fetch_news
from app.services.price_service import fetch_current_price
from app.services.sentiment_service import score_sentiment

Base.metadata.create_all(bind=engine)

PRICE_POLL_INTERVAL_MINUTES = 5
NEWS_POLL_INTERVAL_MINUTES = 10

connected_clients: list[WebSocket] = []
scheduler = AsyncIOScheduler()


async def broadcast(message: dict):
    for client in list(connected_clients):
        try:
            await client.send_json(message)
        except Exception:
            connected_clients.remove(client)


async def poll_prices_job():
    db = SessionLocal()
    try:
        symbols = db.query(models.Symbol).all()
        for symbol in symbols:
            try:
                price = fetch_current_price(symbol.ticker)
            except ValueError:
                continue
            point = models.PricePoint(symbol_id=symbol.id, price=price)
            db.add(point)
            db.commit()
            db.refresh(point)
            await broadcast(
                {
                    "type": "price",
                    "ticker": symbol.ticker,
                    "price": price,
                    "fetched_at": point.fetched_at.isoformat(),
                }
            )
    finally:
        db.close()


async def poll_news_job():
    db = SessionLocal()
    try:
        symbols = db.query(models.Symbol).all()
        for symbol in symbols:
            for item in fetch_news(symbol.ticker):
                sentiment = score_sentiment(item["headline"])
                news_item = models.NewsItem(
                    symbol_id=symbol.id,
                    source=item["source"],
                    headline=item["headline"],
                    url=item["url"],
                    published_at=item["published_at"],
                    sentiment_score=sentiment,
                )
                db.add(news_item)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    continue
                db.refresh(news_item)
                await broadcast(
                    {
                        "type": "news",
                        "ticker": symbol.ticker,
                        "source": news_item.source,
                        "headline": news_item.headline,
                        "url": news_item.url,
                        "published_at": news_item.published_at.isoformat(),
                        "sentiment_score": sentiment,
                    }
                )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(poll_prices_job, "interval", minutes=PRICE_POLL_INTERVAL_MINUTES)
    scheduler.add_job(poll_news_job, "interval", minutes=NEWS_POLL_INTERVAL_MINUTES)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="StockInsight API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/symbols", response_model=SymbolOut)
def add_symbol(payload: SymbolCreate, db: Session = Depends(get_db)):
    ticker = payload.ticker.upper()
    existing = db.query(models.Symbol).filter_by(ticker=ticker).first()
    if existing:
        return existing

    try:
        fetch_current_price(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    symbol = models.Symbol(ticker=ticker)
    db.add(symbol)
    db.commit()
    db.refresh(symbol)
    return symbol


@app.get("/symbols", response_model=list[SymbolOut])
def list_symbols(db: Session = Depends(get_db)):
    return db.query(models.Symbol).all()


@app.get("/symbols/{ticker}/price", response_model=PricePointOut)
def get_price(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    price = fetch_current_price(symbol.ticker)
    point = models.PricePoint(symbol_id=symbol.id, price=price)
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


@app.get("/symbols/{ticker}/news", response_model=list[NewsItemOut])
def get_news(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    return (
        db.query(models.NewsItem)
        .filter_by(symbol_id=symbol.id)
        .order_by(desc(models.NewsItem.published_at))
        .limit(20)
        .all()
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
