import requests

from app.config import settings

FINNHUB_METRIC_URL = "https://finnhub.io/api/v1/stock/metric"
FINNHUB_PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"


def fetch_fundamentals(ticker: str) -> dict:
    metric_resp = requests.get(
        FINNHUB_METRIC_URL,
        params={"symbol": ticker, "metric": "all", "token": settings.finnhub_api_key},
        timeout=10,
    )
    metric_resp.raise_for_status()
    m = metric_resp.json().get("metric", {})

    profile_resp = requests.get(
        FINNHUB_PROFILE_URL,
        params={"symbol": ticker, "token": settings.finnhub_api_key},
        timeout=10,
    )
    profile_resp.raise_for_status()
    p = profile_resp.json()

    return {
        "pe_ttm": m.get("peTTM"),
        "forward_pe": m.get("forwardPE"),
        "peg_ttm": m.get("pegTTM"),
        "cash_flow_per_share_ttm": m.get("cashFlowPerShareTTM"),
        "gross_margin_ttm": m.get("grossMarginTTM"),
        "net_profit_margin_ttm": m.get("netProfitMarginTTM"),
        "operating_margin_ttm": m.get("operatingMarginTTM"),
        "roe_ttm": m.get("roeTTM"),
        "roa_ttm": m.get("roaTTM"),
        "debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
        "dividend_yield_ttm": m.get("currentDividendYieldTTM"),
        "eps_ttm": m.get("epsInclExtraItemsTTM"),
        "eps_growth_3y": m.get("epsGrowth3Y"),
        "eps_growth_5y": m.get("epsGrowth5Y"),
        "eps_growth_ttm_yoy": m.get("epsGrowthTTMYoy"),
        "eps_growth_quarterly_yoy": m.get("epsGrowthQuarterlyYoy"),
        "beta": m.get("beta"),
        "week52_high": m.get("52WeekHigh"),
        "week52_low": m.get("52WeekLow"),
        "market_cap": p.get("marketCapitalization"),
        "industry": p.get("finnhubIndustry"),
    }
