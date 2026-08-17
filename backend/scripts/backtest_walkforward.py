"""
Backtest walk-forward: simula cómo se hubiera comportado el modelo si se
hubiera usado en tiempo real desde `--start`, reentrenando periódicamente
solo con datos pasados (nunca mira el futuro) y prediciendo hacia adelante.

A diferencia de train_models.py (que entrena UNA vez con TODOS los datos
para el modelo que corre en producción), esto es puramente una evaluación:
mide qué tan bien se hubiera comportado el enfoque en la práctica, incluido
un retorno simulado comparado contra comprar-y-mantener (buy-and-hold),
según la métrica de éxito definida en DESIGN.md.

Uso:
    cd backend
    .venv\\Scripts\\python.exe scripts\\backtest_walkforward.py TSM UMC MU --start 2026-01-01
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from app import models
from app.database import SessionLocal
from app.ml.features import FEATURE_COLUMNS, build_features, build_labels

HORIZONS = {"1d": 1, "1w": 5}
MIN_TRAIN_SAMPLES = 60
RETRAIN_EVERY_N_DAYS = 5  # reentrena semanalmente (días hábiles)
BUY_SIGNAL_THRESHOLD = 0.55


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


def backtest_one(ticker: str, horizon_key: str, horizon_days: int, df: pd.DataFrame, start_date: date):
    featured = build_features(df)
    featured["label"] = build_labels(df, horizon_days)
    featured["fwd_return"] = df["close"].shift(-horizon_days) / df["close"] - 1
    data = featured.dropna(subset=FEATURE_COLUMNS + ["label", "fwd_return"]).reset_index(drop=True)

    start_idx = data[data["date"] >= start_date].index.min()
    if pd.isna(start_idx) or start_idx < MIN_TRAIN_SAMPLES:
        print(f"{ticker} [{horizon_key}]: no hay suficiente historia antes de {start_date} para arrancar. Se omite.")
        return None

    model = None
    last_retrain_i = -1
    records = []

    for i in range(start_idx, len(data)):
        if model is None or (i - last_retrain_i) >= RETRAIN_EVERY_N_DAYS:
            train_slice = data.iloc[:i]
            model = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42, class_weight="balanced")
            model.fit(train_slice[FEATURE_COLUMNS], train_slice["label"])
            last_retrain_i = i

        row = data.iloc[i]
        prob_up = model.predict_proba(row[FEATURE_COLUMNS].to_frame().T)[0][1]
        records.append(
            {
                "date": row["date"],
                "prob_up": prob_up,
                "actual_up": row["label"],
                "fwd_return": row["fwd_return"],
            }
        )

    results = pd.DataFrame(records)
    if results.empty:
        print(f"{ticker} [{horizon_key}]: sin días para evaluar desde {start_date}. Se omite.")
        return None

    results["predicted_up"] = (results["prob_up"] >= 0.5).astype(int)
    accuracy = (results["predicted_up"] == results["actual_up"]).mean()

    buy_signals = results[results["prob_up"] >= BUY_SIGNAL_THRESHOLD]
    strategy_avg_return = buy_signals["fwd_return"].mean() if len(buy_signals) > 0 else None
    buy_hold_avg_return = results["fwd_return"].mean()

    print(
        f"{ticker} [{horizon_key}]: {len(results)} días evaluados desde {start_date} | "
        f"accuracy walk-forward={accuracy:.3f} | "
        f"señales de compra (prob>={BUY_SIGNAL_THRESHOLD})={len(buy_signals)} | "
        f"retorno prom. por señal={f'{strategy_avg_return * 100:.2f}%' if strategy_avg_return is not None else 'N/D'} | "
        f"retorno prom. buy-and-hold={buy_hold_avg_return * 100:.2f}%"
    )
    return {
        "ticker": ticker,
        "horizon": horizon_key,
        "n_days": len(results),
        "accuracy": accuracy,
        "n_buy_signals": len(buy_signals),
        "strategy_avg_return": strategy_avg_return,
        "buy_hold_avg_return": buy_hold_avg_return,
    }


def main(tickers: list[str], start_date: date):
    db = SessionLocal()
    all_results = []
    try:
        for ticker in tickers:
            ticker = ticker.upper()
            symbol = db.query(models.Symbol).filter_by(ticker=ticker).first()
            if not symbol:
                print(f"{ticker}: no encontrado. Se omite.")
                continue
            df = load_daily_prices(db, symbol.id)
            if df.empty:
                print(f"{ticker}: sin daily_prices. Se omite.")
                continue
            for horizon_key, horizon_days in HORIZONS.items():
                result = backtest_one(ticker, horizon_key, horizon_days, df, start_date)
                if result:
                    all_results.append(result)
    finally:
        db.close()

    if all_results:
        avg_accuracy = sum(r["accuracy"] for r in all_results) / len(all_results)
        print(f"\nPromedio de accuracy walk-forward across all: {avg_accuracy:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--start", default="2026-01-01")
    args = parser.parse_args()
    main(args.tickers, date.fromisoformat(args.start))
