"""
Entrena los modelos de dirección (sube/baja) por símbolo y horizonte, usando
el histórico diario ya cargado en daily_prices (ver backfill_daily_prices.py).

Corre esto LOCAL. Los modelos entrenados (.joblib) quedan en
app/ml/artifacts/ y se commitean al repo — el backend en Render solo los
carga para inferencia, no entrena nada en producción.

Uso:
    cd backend
    .venv\\Scripts\\python.exe scripts\\train_models.py AAPL MSFT TSM
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from app import models
from app.database import SessionLocal
from app.ml.features import FEATURE_COLUMNS, build_features, build_labels

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"
HORIZONS = {"1d": 1, "1w": 5}  # días hábiles
MIN_SAMPLES = 100


def load_daily_prices(db, symbol_id: int) -> pd.DataFrame:
    rows = (
        db.query(models.DailyPrice)
        .filter_by(symbol_id=symbol_id)
        .order_by(models.DailyPrice.date)
        .all()
    )
    return pd.DataFrame(
        [{"date": r.date, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume} for r in rows]
    )


def train_one(ticker: str, horizon_key: str, horizon_days: int, df: pd.DataFrame) -> dict | None:
    featured = build_features(df)
    featured["label"] = build_labels(df, horizon_days)
    data = featured.dropna(subset=FEATURE_COLUMNS + ["label"])

    if len(data) < MIN_SAMPLES:
        print(f"{ticker} [{horizon_key}]: solo {len(data)} muestras utilizables, se necesitan {MIN_SAMPLES}+. Se omite.")
        return None

    split = int(len(data) * 0.8)
    train, test = data.iloc[:split], data.iloc[split:]

    model = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)
    model.fit(train[FEATURE_COLUMNS], train["label"])

    accuracy = None
    if len(test) > 0:
        preds = model.predict(test[FEATURE_COLUMNS])
        accuracy = float(accuracy_score(test["label"], preds))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"{ticker}_{horizon_key}.joblib"
    joblib.dump(
        {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
            "ticker": ticker,
            "horizon": horizon_key,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "n_samples": len(data),
            "test_accuracy": accuracy,
        },
        artifact_path,
    )
    print(f"{ticker} [{horizon_key}]: entrenado con {len(data)} muestras, accuracy test={accuracy}")
    return {"ticker": ticker, "horizon": horizon_key, "accuracy": accuracy}


def main(tickers: list[str]):
    db = SessionLocal()
    try:
        for ticker in tickers:
            ticker = ticker.upper()
            symbol = db.query(models.Symbol).filter_by(ticker=ticker).first()
            if not symbol:
                print(f"{ticker}: no encontrado en symbols (corré primero el backfill). Se omite.")
                continue

            df = load_daily_prices(db, symbol.id)
            if df.empty:
                print(f"{ticker}: sin daily_prices, corré primero el backfill. Se omite.")
                continue

            for horizon_key, horizon_days in HORIZONS.items():
                train_one(ticker, horizon_key, horizon_days, df)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/train_models.py TICKER [TICKER ...]")
        sys.exit(1)
    main(sys.argv[1:])
