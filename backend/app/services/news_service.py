from calendar import timegm
from datetime import datetime, timezone

import feedparser

YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"


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
        feed = feedparser.parse(url)
    except Exception:
        return []

    items = []
    for entry in feed.entries:
        item = _entry_to_item(entry, source)
        if item:
            items.append(item)
    return items


def fetch_news(ticker: str) -> list[dict]:
    items = []
    items.extend(_fetch_feed(YAHOO_RSS_URL.format(ticker=ticker), "Yahoo Finance"))
    items.extend(_fetch_feed(GOOGLE_NEWS_RSS_URL.format(ticker=ticker), "Google News"))
    return items
