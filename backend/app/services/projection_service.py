"""
Heurística PRELIMINAR de precio objetivo — NO es el modelo de ML planeado en
ARCHITECTURE.md (ese requiere semanas/meses de histórico propio para
entrenarse con calidad). Esto es un placeholder simple, basado en tendencia
reciente del precio + sentimiento de noticias, para tener algo mostrable
mientras se acumula suficiente data para el modelo real.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models

# Cuánto puede desviarse el proyectado del precio actual, como máximo, por horizonte.
MAX_MOVE = {
    "target_price_1w": 0.07,
    "target_price_1m": 0.15,
    "target_price_1y": 0.30,
}
HORIZON_DAYS = {
    "target_price_1w": 7,
    "target_price_1m": 30,
    "target_price_1y": 365,
}
SENTIMENT_IMPACT_PER_DAY = 0.001  # hasta ~0.1% de drift diario extra por sentimiento máximo


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _daily_trend(db: Session, symbol_id: int) -> float:
    points = (
        db.query(models.PricePoint)
        .filter(models.PricePoint.symbol_id == symbol_id)
        .order_by(models.PricePoint.fetched_at)
        .all()
    )
    if len(points) < 2:
        return 0.0

    first, last = points[0], points[-1]
    elapsed = last.fetched_at.replace(tzinfo=timezone.utc) - first.fetched_at.replace(tzinfo=timezone.utc)
    if elapsed.total_seconds() < 3600 or first.price == 0:
        return 0.0

    elapsed_days_num = elapsed.total_seconds() / 86400
    total_change = (last.price - first.price) / first.price
    return _clamp(total_change / elapsed_days_num, -0.02, 0.02)


def project_target_prices(db: Session, symbol_id: int, current_price: float, sentiment_medium: float | None) -> dict:
    daily_drift = _daily_trend(db, symbol_id)
    sentiment_drift = (sentiment_medium or 0.0) * SENTIMENT_IMPACT_PER_DAY
    total_daily_drift = daily_drift + sentiment_drift

    targets = {}
    for key, days in HORIZON_DAYS.items():
        raw_move = total_daily_drift * days
        capped_move = _clamp(raw_move, -MAX_MOVE[key], MAX_MOVE[key])
        targets[key] = round(current_price * (1 + capped_move), 2)

    targets["is_preliminary"] = True
    return targets
