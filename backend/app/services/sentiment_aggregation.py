from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

SHORT_TERM_WINDOW = timedelta(days=1)
MEDIUM_TERM_WINDOW = timedelta(days=7)
LONG_TERM_WINDOW = timedelta(days=30)


def _avg_sentiment_since(db: Session, symbol_id: int, since: datetime) -> float | None:
    result = (
        db.query(func.avg(models.NewsItem.sentiment_score))
        .filter(models.NewsItem.symbol_id == symbol_id, models.NewsItem.published_at >= since)
        .scalar()
    )
    return float(result) if result is not None else None


def aggregate_sentiment(db: Session, symbol_id: int) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "short_term": _avg_sentiment_since(db, symbol_id, now - SHORT_TERM_WINDOW),
        "medium_term": _avg_sentiment_since(db, symbol_id, now - MEDIUM_TERM_WINDOW),
        "long_term": _avg_sentiment_since(db, symbol_id, now - LONG_TERM_WINDOW),
    }
