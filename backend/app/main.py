from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.schemas.symbol import PricePointOut, SymbolCreate, SymbolOut
from app.services.price_service import fetch_current_price

Base.metadata.create_all(bind=engine)

PRICE_POLL_INTERVAL_MINUTES = 5

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
                    "ticker": symbol.ticker,
                    "price": price,
                    "fetched_at": point.fetched_at.isoformat(),
                }
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(poll_prices_job, "interval", minutes=PRICE_POLL_INTERVAL_MINUTES)
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
