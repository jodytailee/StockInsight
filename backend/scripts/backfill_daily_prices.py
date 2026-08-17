"""
Trae histórico diario (2 años) de precio vía yfinance y lo guarda en
daily_prices, para poder entrenar los modelos ML.

Corre esto LOCAL (no en Render) — yfinance funciona bien para consultas
puntuales como esta, el bloqueo que vimos en producción era por volumen de
llamadas en vivo desde una IP de datacenter compartida.

Uso:
    cd backend
    .venv\\Scripts\\python.exe scripts\\backfill_daily_prices.py AAPL MSFT TSM
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yfinance as yf

from app import models
from app.database import Base, SessionLocal, engine


def backfill(ticker: str):
    ticker = ticker.upper()
    df = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=False)
    if df.empty:
        print(f"{ticker}: sin datos, se omite")
        return

    db = SessionLocal()
    try:
        symbol = db.query(models.Symbol).filter_by(ticker=ticker).first()
        if not symbol:
            symbol = models.Symbol(ticker=ticker)
            db.add(symbol)
            db.commit()
            db.refresh(symbol)

        existing_dates = {
            d for (d,) in db.query(models.DailyPrice.date).filter_by(symbol_id=symbol.id).all()
        }

        added = 0
        for idx, row in df.iterrows():
            day = idx.date()
            if day in existing_dates:
                continue
            db.add(
                models.DailyPrice(
                    symbol_id=symbol.id,
                    date=day,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
            added += 1
        db.commit()
        print(f"{ticker}: {added} días nuevos agregados ({len(df)} descargados)")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/backfill_daily_prices.py TICKER [TICKER ...]")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    for t in sys.argv[1:]:
        backfill(t)
