from apscheduler.schedulers.blocking import BlockingScheduler

from app import models
from app.database import SessionLocal
from app.services.price_service import fetch_current_price

PRICE_POLL_INTERVAL_MINUTES = 5


def poll_prices():
    db = SessionLocal()
    try:
        symbols = db.query(models.Symbol).all()
        for symbol in symbols:
            try:
                price = fetch_current_price(symbol.ticker)
            except ValueError:
                continue
            db.add(models.PricePoint(symbol_id=symbol.id, price=price))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(poll_prices, "interval", minutes=PRICE_POLL_INTERVAL_MINUTES)
    print(f"StockInsight scheduler running (poll every {PRICE_POLL_INTERVAL_MINUTES} min). Ctrl+C to stop.")
    scheduler.start()
