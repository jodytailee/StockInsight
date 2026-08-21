from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SymbolCreate(BaseModel):
    ticker: str
    quantity: float | None = None
    avg_cost: float | None = None


class SymbolPositionUpdate(BaseModel):
    quantity: float | None = None
    avg_cost: float | None = None


class PositionLotCreate(BaseModel):
    quantity: float
    price: float
    purchased_at: datetime | None = None


class PositionLotUpdate(BaseModel):
    quantity: float | None = None
    price: float | None = None
    purchased_at: datetime | None = None


class PositionLotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: float
    price: float
    purchased_at: datetime


class SymbolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    created_at: datetime
    quantity: float | None = None
    avg_cost: float | None = None


class PricePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: float
    fetched_at: datetime


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    headline: str
    url: str
    published_at: datetime
    sentiment_score: float


class MlDirectionOut(BaseModel):
    probability_up: float
    test_accuracy: float | None
    trained_at: str
    n_samples: int


class RecommendationOut(BaseModel):
    action: str
    expected_return_pct: float


class AiAnalysisOut(BaseModel):
    text: str
    generated_at: datetime


class FundamentalsOut(BaseModel):
    pe_ttm: float | None
    forward_pe: float | None
    peg_ttm: float | None
    cash_flow_per_share_ttm: float | None
    gross_margin_ttm: float | None
    net_profit_margin_ttm: float | None
    operating_margin_ttm: float | None
    roe_ttm: float | None
    roa_ttm: float | None
    debt_to_equity: float | None
    dividend_yield_ttm: float | None
    eps_ttm: float | None
    beta: float | None
    week52_high: float | None
    week52_low: float | None
    market_cap: float | None
    industry: str | None
    eps_growth_3y: float | None = None
    eps_growth_5y: float | None = None
    eps_growth_ttm_yoy: float | None = None
    eps_growth_quarterly_yoy: float | None = None


class EpsAnalysisOut(BaseModel):
    quality_label: str
    growth_explanation: str
    pe_context: str | None
    eps_growth_3y: float | None
    eps_growth_5y: float | None
    eps_growth_ttm_yoy: float | None
    eps_growth_quarterly_yoy: float | None


class InsightsOut(BaseModel):
    sentiment_short_term: float | None
    sentiment_medium_term: float | None
    sentiment_long_term: float | None
    analyst_rating: str
    analyst_counts: dict | None
    target_price_1w: float
    target_price_1m: float
    target_price_1y: float
    is_preliminary_projection: bool = True
    ml_direction_1d: MlDirectionOut | None = None
    ml_direction_1w: MlDirectionOut | None = None
    fundamentals: FundamentalsOut | None = None
    eps_analysis: EpsAnalysisOut | None = None
    quantity: float | None = None
    avg_cost: float | None = None
    unrealized_pnl_pct: float | None = None
    recommendation_1w: RecommendationOut
    recommendation_1m: RecommendationOut
    recommendation_1y: RecommendationOut
