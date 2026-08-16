import yfinance as yf


def fetch_current_price(ticker: str) -> float:
    stock = yf.Ticker(ticker)
    price = stock.fast_info.get("last_price")
    if price is None:
        raise ValueError(f"No se pudo obtener el precio de {ticker}")
    return float(price)
