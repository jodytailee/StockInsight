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
    quantity: float | None = None
    avg_cost: float | None = None
    unrealized_pnl_pct: float | None = None
    recommendation_1w: RecommendationOut
    recommendation_1m: RecommendationOut
    recommendation_1y: RecommendationOut
