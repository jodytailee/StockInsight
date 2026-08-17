import pandas as pd

FEATURE_COLUMNS = ["return_1d", "sma5_ratio", "sma20_ratio", "rsi14", "momentum_5", "volatility_20", "volume_change"]


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """df debe tener columnas: date, open, high, low, close, volume, ordenado ascendente por fecha."""
    out = df.copy()
    out["return_1d"] = out["close"].pct_change(1)
    out["sma5_ratio"] = out["close"] / out["close"].rolling(5).mean() - 1
    out["sma20_ratio"] = out["close"] / out["close"].rolling(20).mean() - 1
    out["rsi14"] = _rsi(out["close"], 14)
    out["momentum_5"] = out["close"] / out["close"].shift(5) - 1
    out["volatility_20"] = out["return_1d"].rolling(20).std()
    out["volume_change"] = out["volume"] / out["volume"].rolling(20).mean() - 1
    return out


def build_labels(df: pd.DataFrame, horizon_days: int) -> pd.Series:
    """1 si el precio sube en `horizon_days` días hábiles, 0 si baja/igual."""
    future_close = df["close"].shift(-horizon_days)
    return (future_close > df["close"]).astype(int)
