"""
Registra un snapshot diario de la dirección pronosticada (sube/baja) por
símbolo y horizonte, y más adelante resuelve esos pronósticos comparando
contra el precio real — para poder reportar accuracy acumulado real, no
solo el accuracy de validación del entrenamiento.
"""

from datetime import datetime, timedelta, timezone

from app import models
from app.ml.predict import predict_direction
from app.services.projection_service import project_target_prices
from app.services.sentiment_aggregation import aggregate_sentiment

HORIZON_DELTAS = {
    "1d": timedelta(days=1),
    "1w": timedelta(days=7),
    "1m": timedelta(days=30),
}
RESOLUTION_TOLERANCE = timedelta(hours=36)


def _get_current_price(db, symbol_id: int) -> float | None:
    point = (
        db.query(models.PricePoint)
        .filter_by(symbol_id=symbol_id)
        .order_by(models.PricePoint.fetched_at.desc())
        .first()
    )
    return point.price if point else None


def _closest_price_point(db, symbol_id: int, target_date: datetime):
    points = (
        db.query(models.PricePoint)
        .filter(
            models.PricePoint.symbol_id == symbol_id,
            models.PricePoint.fetched_at >= target_date - RESOLUTION_TOLERANCE,
            models.PricePoint.fetched_at <= target_date + RESOLUTION_TOLERANCE,
        )
        .all()
    )
    if not points:
        return None
    return min(points, key=lambda p: abs((p.fetched_at.replace(tzinfo=timezone.utc) - target_date).total_seconds()))


def resolve_due_predictions(db):
    now = datetime.now(timezone.utc)
    due = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.resolved.is_(False), models.PredictionLog.target_date <= now)
        .all()
    )
    for pred in due:
        point = _closest_price_point(db, pred.symbol_id, pred.target_date.replace(tzinfo=timezone.utc))
        if not point:
            continue

        actual_direction = "up" if point.price > pred.price_at_prediction else "down"
        pred.resolved = True
        pred.resolved_at = now
        pred.price_at_resolution = point.price
        pred.actual_direction = actual_direction
        pred.was_correct = actual_direction == pred.predicted_direction
        db.commit()


def _predict_for_horizon(db, symbol, horizon: str, current_price: float, sentiment_medium: float | None) -> dict:
    if horizon in ("1d", "1w"):
        ml = predict_direction(db, symbol.id, symbol.ticker, horizon, current_price)
        if ml:
            direction = "up" if ml["probability_up"] >= 0.5 else "down"
            return {"source": "ml", "direction": direction, "probability_up": ml["probability_up"]}

    targets = project_target_prices(db, symbol.id, current_price, sentiment_medium)
    target_key = {"1d": "target_price_1w", "1w": "target_price_1w", "1m": "target_price_1m"}[horizon]
    direction = "up" if targets[target_key] >= current_price else "down"
    return {"source": "heuristic", "direction": direction, "probability_up": None}


def log_new_predictions(db):
    now = datetime.now(timezone.utc)
    symbols = db.query(models.Symbol).all()
    for symbol in symbols:
        current_price = _get_current_price(db, symbol.id)
        if current_price is None:
            continue
        sentiment = aggregate_sentiment(db, symbol.id)

        for horizon, delta in HORIZON_DELTAS.items():
            already_logged = (
                db.query(models.PredictionLog)
                .filter(
                    models.PredictionLog.symbol_id == symbol.id,
                    models.PredictionLog.horizon == horizon,
                    models.PredictionLog.predicted_at >= now - timedelta(hours=20),
                )
                .first()
            )
            if already_logged:
                continue

            pred = _predict_for_horizon(db, symbol, horizon, current_price, sentiment["medium_term"])
            db.add(
                models.PredictionLog(
                    symbol_id=symbol.id,
                    horizon=horizon,
                    source=pred["source"],
                    predicted_at=now,
                    target_date=now + delta,
                    price_at_prediction=current_price,
                    predicted_direction=pred["direction"],
                    probability_up=pred["probability_up"],
                )
            )
            db.commit()


def get_recently_resolved(db, symbol_id: int, since: datetime) -> list[models.PredictionLog]:
    return (
        db.query(models.PredictionLog)
        .filter(
            models.PredictionLog.symbol_id == symbol_id,
            models.PredictionLog.resolved.is_(True),
            models.PredictionLog.resolved_at >= since,
        )
        .order_by(models.PredictionLog.horizon)
        .all()
    )


def get_accuracy_summary(db, symbol_id: int) -> dict:
    resolved = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.symbol_id == symbol_id, models.PredictionLog.resolved.is_(True))
        .all()
    )
    summary = {}
    for horizon in HORIZON_DELTAS:
        rows = [r for r in resolved if r.horizon == horizon]
        total = len(rows)
        correct = sum(1 for r in rows if r.was_correct)
        summary[horizon] = {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(correct / total * 100, 1) if total else None,
        }
    return summary
