from calendar import timegm
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests

YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"

# Noticias de mercado en general (no atadas a un ticker) — tasas de interés,
# geopolítica, inflación, etc. — para el símbolo pseudo "GENERAL".
GENERAL_MARKET_QUERY = (
    "stock market OR \"Federal Reserve\" OR \"interest rates\" OR inflation OR recession "
    "OR geopolitical OR tariffs OR war"
)
GOOGLE_NEWS_GENERAL_URL = (
    f"https://news.google.com/rss/search?q={quote(GENERAL_MARKET_QUERY)}&hl=en-US&gl=US&ceid=US:en"
)

# Algunos servidores bloquean el User-Agent por defecto de requests/feedparser.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockInsightBot/1.0; +https://stockinsight.ticolab.app)"}


def _entry_to_item(entry, source: str) -> dict | None:
    if not getattr(entry, "published_parsed", None):
        return None
    published_at = datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
    return {
        "source": source,
        "headline": entry.title,
        "url": entry.link,
        "published_at": published_at,
    }


def _fetch_feed(url: str, source: str) -> list[dict]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[news] {source} fetch failed ({url}): {type(e).__name__} {e}")
        return []

    feed = feedparser.parse(response.content)
    if feed.bozo:
        print(f"[news] {source} feed parse warning ({url}): {feed.bozo_exception}")

    items = []
    for entry in feed.entries:
        item = _entry_to_item(entry, source)
        if item:
            items.append(item)

    if not items:
        print(f"[news] {source} returned 0 entries for {url} (status={response.status_code})")

    return items


def fetch_news(ticker: str) -> list[dict]:
    items = []
    items.extend(_fetch_feed(YAHOO_RSS_URL.format(ticker=ticker), "Yahoo Finance"))
    items.extend(_fetch_feed(GOOGLE_NEWS_RSS_URL.format(ticker=ticker), "Google News"))
    return items


def fetch_general_market_news() -> list[dict]:
    return _fetch_feed(GOOGLE_NEWS_GENERAL_URL, "Google News")
