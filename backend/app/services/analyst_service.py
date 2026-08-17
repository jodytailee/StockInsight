import requests

from app.config import settings

FINNHUB_RECOMMENDATION_URL = "https://finnhub.io/api/v1/stock/recommendation"

RATING_STRONG_BUY = "Strong Buy"
RATING_BUY = "Buy"
RATING_NEUTRAL = "Neutral"
RATING_SELL = "Sell"
RATING_STRONG_SELL = "Strong Sell"
RATING_NO_DATA = "No data"


def _label_from_score(score: float) -> str:
    if score >= 1.5:
        return RATING_STRONG_BUY
    if score >= 0.5:
        return RATING_BUY
    if score > -0.5:
        return RATING_NEUTRAL
    if score > -1.5:
        return RATING_SELL
    return RATING_STRONG_SELL


def fetch_analyst_rating(ticker: str) -> dict:
    response = requests.get(
        FINNHUB_RECOMMENDATION_URL,
        params={"symbol": ticker, "token": settings.finnhub_api_key},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        return {"rating": RATING_NO_DATA, "counts": None}

    latest = data[0]  # Finnhub devuelve ordenado del período más reciente al más viejo
    counts = {
        "strongBuy": latest.get("strongBuy", 0),
        "buy": latest.get("buy", 0),
        "hold": latest.get("hold", 0),
        "sell": latest.get("sell", 0),
        "strongSell": latest.get("strongSell", 0),
    }
    total = sum(counts.values())
    if total == 0:
        return {"rating": RATING_NO_DATA, "counts": counts}

    score = (
        counts["strongBuy"] * 2
        + counts["buy"] * 1
        + counts["hold"] * 0
        + counts["sell"] * -1
        + counts["strongSell"] * -2
    ) / total

    return {"rating": _label_from_score(score), "counts": counts}
