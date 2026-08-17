from datetime import date as date_, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    prices: Mapped[list["PricePoint"]] = relationship(back_populates="symbol", cascade="all, delete-orphan")
    news: Mapped[list["NewsItem"]] = relationship(back_populates="symbol", cascade="all, delete-orphan")
    daily_prices: Mapped[list["DailyPrice"]] = relationship(back_populates="symbol", cascade="all, delete-orphan")


class PricePoint(Base):
    __tablename__ = "price_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    price: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    symbol: Mapped["Symbol"] = relationship(back_populates="prices")


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("symbol_id", "url", name="uq_news_symbol_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    source: Mapped[str] = mapped_column(String(50))
    headline: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    published_at: Mapped[datetime] = mapped_column(DateTime)
    sentiment_score: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    symbol: Mapped["Symbol"] = relationship(back_populates="news")


class DailyPrice(Base):
    """Histórico diario (OHLCV) usado para entrenar los modelos ML — poblado
    por backfill desde yfinance, no por el scheduler en vivo."""

    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("symbol_id", "date", name="uq_daily_price_symbol_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    date: Mapped[date_] = mapped_column(Date)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    symbol: Mapped["Symbol"] = relationship(back_populates="daily_prices")
