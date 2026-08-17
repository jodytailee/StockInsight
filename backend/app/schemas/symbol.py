from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SymbolCreate(BaseModel):
    ticker: str


class SymbolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    created_at: datetime


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
