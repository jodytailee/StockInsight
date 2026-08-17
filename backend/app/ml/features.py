import pandas as pd

FEATURE_COLUMNS = [
    "return_1d",
    "sma5_ratio",
    "sma20_ratio",
    "rsi14",
    "momentum_5",
    "momentum_10",
    "volatility_20",
    "volume_change",
    "macd",
    "macd_signal",
    "bollinger_width",
    "atr14",
    "roc10",
    "dist_from_52w_high",
]


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.rolling(window).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """df debe tener columnas: date, open, high, low, close, volume, ordenado ascendente por fecha."""
    out = df.copy()
    out["return_1d"] = out["close"].pct_change(1)
    sma20 = out["close"].rolling(20).mean()
    out["sma5_ratio"] = out["close"] / out["close"].rolling(5).mean() - 1
    out["sma20_ratio"] = out["close"] / sma20 - 1
    out["rsi14"] = _rsi(out["close"], 14)
    out["momentum_5"] = out["close"] / out["close"].shift(5) - 1
    out["momentum_10"] = out["close"] / out["close"].shift(10) - 1
    out["volatility_20"] = out["return_1d"].rolling(20).std()
    out["volume_change"] = out["volume"] / out["volume"].rolling(20).mean() - 1

    macd_line, signal_line = _macd(out["close"])
    out["macd"] = macd_line
    out["macd_signal"] = signal_line

    rolling_std20 = out["close"].rolling(20).std()
    out["bollinger_width"] = (4 * rolling_std20) / sma20

    out["atr14"] = _atr(out["high"], out["low"], out["close"], 14) / out["close"]
    out["roc10"] = out["close"] / out["close"].shift(10) - 1
    out["dist_from_52w_high"] = out["close"] / out["close"].rolling(252).max() - 1
    return out


def build_labels(df: pd.DataFrame, horizon_days: int) -> pd.Series:
    """1 si el precio sube en `horizon_days` días hábiles, 0 si baja/igual."""
    future_close = df["close"].shift(-horizon_days)
    return (future_close > df["close"]).astype(int)
