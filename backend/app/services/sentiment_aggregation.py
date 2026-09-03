from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

SHORT_TERM_WINDOW = timedelta(days=1)
MEDIUM_TERM_WINDOW = timedelta(days=7)
LONG_TERM_WINDOW = timedelta(days=30)

GENERAL_TICKER = "GENERAL"
GENERAL_WEIGHT = 0.25  # cuánto pesa el sentimiento de mercado general vs. el específico del ticker


def _avg_sentiment_since(db: Session, symbol_id: int, since: datetime) -> float | None:
    result = (
        db.query(func.avg(models.NewsItem.sentiment_score))
        .filter(models.NewsItem.symbol_id == symbol_id, models.NewsItem.published_at >= since)
        .scalar()
    )
    return float(result) if result is not None else None


def _blend(specific: float | None, general: float | None) -> float | None:
    if specific is None:
        return general
    if general is None:
        return specific
    return specific * (1 - GENERAL_WEIGHT) + general * GENERAL_WEIGHT


def aggregate_sentiment(db: Session, symbol_id: int) -> dict:
    now = datetime.now(timezone.utc)
    specific = {
        "short_term": _avg_sentiment_since(db, symbol_id, now - SHORT_TERM_WINDOW),
        "medium_term": _avg_sentiment_since(db, symbol_id, now - MEDIUM_TERM_WINDOW),
        "long_term": _avg_sentiment_since(db, symbol_id, now - LONG_TERM_WINDOW),
    }

    general_symbol = db.query(models.Symbol).filter_by(ticker=GENERAL_TICKER).first()
    if not general_symbol or general_symbol.id == symbol_id:
        return specific

    general = {
        "short_term": _avg_sentiment_since(db, general_symbol.id, now - SHORT_TERM_WINDOW),
        "medium_term": _avg_sentiment_since(db, general_symbol.id, now - MEDIUM_TERM_WINDOW),
        "long_term": _avg_sentiment_since(db, general_symbol.id, now - LONG_TERM_WINDOW),
    }

    return {key: _blend(specific[key], general[key]) for key in specific}
