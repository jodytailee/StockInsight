from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app import models
from app.database import Base, SessionLocal, engine, get_db
from app.schemas.symbol import PricePointOut, SymbolCreate, SymbolOut
from app.services.price_service import fetch_current_price

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockInsight API")

connected_clients: list[WebSocket] = []


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
