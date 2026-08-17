from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from app import models
from app.ml.features import FEATURE_COLUMNS, build_features

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

_cache: dict[str, dict | None] = {}


def _load_artifact(ticker: str, horizon_key: str) -> dict | None:
    cache_key = f"{ticker}_{horizon_key}"
    if cache_key in _cache:
        return _cache[cache_key]

    path = ARTIFACTS_DIR / f"{cache_key}.joblib"
    artifact = joblib.load(path) if path.exists() else None
    _cache[cache_key] = artifact
    return artifact


def _load_price_frame(db, symbol_id: int, latest_live_price: float | None) -> pd.DataFrame:
    rows = (
        db.query(models.DailyPrice)
        .filter_by(symbol_id=symbol_id)
        .order_by(models.DailyPrice.date)
        .all()
    )
    df = pd.DataFrame(
        [{"date": r.date, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume} for r in rows]
    )

    if latest_live_price and (df.empty or df.iloc[-1]["date"] < date.today()):
        today_row = {
            "date": date.today(),
            "open": latest_live_price,
            "high": latest_live_price,
            "low": latest_live_price,
            "close": latest_live_price,
            "volume": df.iloc[-1]["volume"] if not df.empty else 0.0,
        }
        df = pd.concat([df, pd.DataFrame([today_row])], ignore_index=True)

    return df


def predict_direction(db, symbol_id: int, ticker: str, horizon_key: str, latest_live_price: float | None) -> dict | None:
    artifact = _load_artifact(ticker.upper(), horizon_key)
    if artifact is None:
        return None

    df = _load_price_frame(db, symbol_id, latest_live_price)
    if len(df) < 25:
        return None

    featured = build_features(df)
    last_row = featured.iloc[-1]
    if last_row[FEATURE_COLUMNS].isnull().any():
        return None

    model = artifact["model"]
    probability_up = float(model.predict_proba(last_row[FEATURE_COLUMNS].to_frame().T)[0][1])

    return {
        "probability_up": probability_up,
        "trained_at": artifact["trained_at"],
        "test_accuracy": artifact["test_accuracy"],
        "n_samples": artifact["n_samples"],
    }
