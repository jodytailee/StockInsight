import requests

from app.config import settings

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"


def fetch_current_price(ticker: str) -> float:
    response = requests.get(
        FINNHUB_QUOTE_URL,
        params={"symbol": ticker, "token": settings.finnhub_api_key},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    price = data.get("c")  # "current price" en la respuesta de Finnhub
    if not price:
        raise ValueError(f"No se pudo obtener el precio de {ticker}")
    return float(price)
