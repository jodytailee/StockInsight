from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, inspect, text
from sqlalchemy.exc import IntegrityError, NoSuchTableError
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.schemas.symbol import (
    AiAnalysisOut,
    EpsAnalysisOut,
    InsightsOut,
    NewsItemOut,
    PositionLotCreate,
    PositionLotOut,
    PositionLotUpdate,
    PricePointOut,
    SymbolCreate,
    SymbolOut,
    SymbolPositionUpdate,
)
from app.ml.predict import predict_direction
from app.services.ai_analysis_service import generate_analysis
from app.services.analyst_service import fetch_analyst_rating
from app.services.digest_service import build_daily_digest_html
from app.services.email_service import send_email
from app.services.eps_analysis_service import analyze_eps
from app.services.fundamentals_service import fetch_fundamentals
from app.services.news_classification_service import classify_batch
from app.services.news_service import fetch_general_market_news, fetch_news
from app.services.position_service import refresh_symbol_position
from app.services.prediction_tracking_service import log_new_predictions, resolve_due_predictions
from app.services.price_service import fetch_current_price
from app.services.projection_service import project_target_prices
from app.services.recommendation_service import generate_recommendations
from app.services.sentiment_aggregation import aggregate_sentiment
from app.services.sentiment_service import score_sentiment
from app.services.training_dispatch_service import trigger_training


def _ensure_symbol_columns():
    """Migración liviana ad-hoc: agrega columnas nuevas a `symbols` si la
    tabla ya existía de antes (create_all no altera tablas existentes)."""
    try:
        columns = {c["name"] for c in inspect(engine).get_columns("symbols")}
    except NoSuchTableError:
        return

    with engine.begin() as conn:
        if "quantity" not in columns:
            conn.execute(text("ALTER TABLE symbols ADD COLUMN quantity FLOAT"))
        if "avg_cost" not in columns:
            conn.execute(text("ALTER TABLE symbols ADD COLUMN avg_cost FLOAT"))
        if "ai_analysis" not in columns:
            conn.execute(text("ALTER TABLE symbols ADD COLUMN ai_analysis TEXT"))
        if "ai_analysis_generated_at" not in columns:
            conn.execute(text("ALTER TABLE symbols ADD COLUMN ai_analysis_generated_at TIMESTAMP"))


def _ensure_news_columns():
    try:
        columns = {c["name"] for c in inspect(engine).get_columns("news_items")}
    except NoSuchTableError:
        return

    with engine.begin() as conn:
        if "topic" not in columns:
            conn.execute(text("ALTER TABLE news_items ADD COLUMN topic VARCHAR(30)"))
        if "scope" not in columns:
            conn.execute(text("ALTER TABLE news_items ADD COLUMN scope VARCHAR(20)"))
        if "impact_direction" not in columns:
            conn.execute(text("ALTER TABLE news_items ADD COLUMN impact_direction VARCHAR(10)"))
        if "classified_at" not in columns:
            conn.execute(text("ALTER TABLE news_items ADD COLUMN classified_at TIMESTAMP"))


Base.metadata.create_all(bind=engine)
_ensure_symbol_columns()
_ensure_news_columns()


def _require_cron_secret(x_cron_secret: str | None = Header(default=None), secret: str | None = None):
    """Los endpoints /cron/* los dispara un servicio externo (cron-job.org),
    no el propio scheduler (Vercel no soporta procesos persistentes) — así
    que están abiertos a internet y necesitan este chequeo para que no
    cualquiera los dispare a mano."""
    if not settings.cron_secret:
        return  # sin secreto configurado, no se exige (solo para desarrollo local)
    provided = x_cron_secret or secret
    if provided != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing cron secret")


def poll_prices_job():
    db = SessionLocal()
    try:
        symbols = db.query(models.Symbol).all()
        for symbol in symbols:
            try:
                price = fetch_current_price(symbol.ticker)
            except ValueError:
                continue
            db.add(models.PricePoint(symbol_id=symbol.id, price=price))
            db.commit()
    finally:
        db.close()


GENERAL_TICKER = "GENERAL"


def _get_or_create_general_symbol(db) -> models.Symbol:
    symbol = db.query(models.Symbol).filter_by(ticker=GENERAL_TICKER).first()
    if not symbol:
        symbol = models.Symbol(ticker=GENERAL_TICKER)
        db.add(symbol)
        db.commit()
        db.refresh(symbol)
    return symbol


def poll_news_job():
    db = SessionLocal()
    try:
        symbols = db.query(models.Symbol).filter(models.Symbol.ticker != GENERAL_TICKER).all()
        general_symbol = _get_or_create_general_symbol(db)

        new_items: list[tuple[models.NewsItem, str, bool]] = []  # (item, ticker, is_general)

        def save_items(symbol: models.Symbol, raw_items: list[dict], is_general: bool):
            for item in raw_items:
                sentiment = score_sentiment(item["headline"])
                news_item = models.NewsItem(
                    symbol_id=symbol.id,
                    source=item["source"],
                    headline=item["headline"],
                    url=item["url"],
                    published_at=item["published_at"],
                    sentiment_score=sentiment,
                )
                db.add(news_item)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    continue
                db.refresh(news_item)
                new_items.append((news_item, symbol.ticker, is_general))

        for symbol in symbols:
            save_items(symbol, fetch_news(symbol.ticker), is_general=False)
        save_items(general_symbol, fetch_general_market_news(), is_general=True)

        if new_items:
            batch_input = [{"ticker": ticker, "headline": item.headline} for item, ticker, _ in new_items]
            classifications = classify_batch(batch_input)
            for (item, _ticker, is_general), cls in zip(new_items, classifications):
                if not cls:
                    continue
                item.topic = cls.get("topic")
                item.scope = cls.get("scope") or ("market_wide" if is_general else None)
                item.impact_direction = cls.get("impact_direction")
                item.classified_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def send_daily_digest_job():
    db = SessionLocal()
    try:
        html = build_daily_digest_html(db)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        send_email(f"StockInsight — Resumen diario ({today})", html)
    finally:
        db.close()


def track_predictions_job():
    db = SessionLocal()
    try:
        resolve_due_predictions(db)
        log_new_predictions(db)
    finally:
        db.close()


app = FastAPI(title="StockInsight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        {
            "http://localhost:5173",
            "https://stock-insight-navy.vercel.app",
            "https://stockinsight.ticolab.app",
            settings.frontend_url,
        }
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/cron/poll-prices", dependencies=[Depends(_require_cron_secret)])
def cron_poll_prices():
    poll_prices_job()
    return {"status": "done"}


@app.post("/cron/poll-news", dependencies=[Depends(_require_cron_secret)])
def cron_poll_news():
    poll_news_job()
    return {"status": "done"}


@app.post("/cron/track-predictions", dependencies=[Depends(_require_cron_secret)])
def cron_track_predictions():
    track_predictions_job()
    return {"status": "done"}


@app.post("/cron/send-digest", dependencies=[Depends(_require_cron_secret)])
def cron_send_digest():
    send_daily_digest_job()
    return {"status": "sent"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/symbols", response_model=SymbolOut)
def add_symbol(payload: SymbolCreate, db: Session = Depends(get_db)):
    ticker = payload.ticker.upper()
    existing = db.query(models.Symbol).filter_by(ticker=ticker).first()
    if existing:
        if payload.quantity is not None:
            existing.quantity = payload.quantity
        if payload.avg_cost is not None:
            existing.avg_cost = payload.avg_cost
        db.commit()
        db.refresh(existing)
        return existing

    try:
        fetch_current_price(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    symbol = models.Symbol(ticker=ticker, quantity=payload.quantity, avg_cost=payload.avg_cost)
    db.add(symbol)
    db.commit()
    db.refresh(symbol)

    trigger_training(ticker)

    return symbol


@app.patch("/symbols/{ticker}/position", response_model=SymbolOut)
def update_position(ticker: str, payload: SymbolPositionUpdate, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    if payload.quantity is not None:
        symbol.quantity = payload.quantity
    if payload.avg_cost is not None:
        symbol.avg_cost = payload.avg_cost
    db.commit()
    db.refresh(symbol)
    return symbol


@app.get("/symbols", response_model=list[SymbolOut])
def list_symbols(db: Session = Depends(get_db)):
    return db.query(models.Symbol).filter(models.Symbol.ticker != GENERAL_TICKER).all()


@app.get("/symbols/{ticker}/price", response_model=PricePointOut)
def get_price(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    try:
        price = fetch_current_price(symbol.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    point = models.PricePoint(symbol_id=symbol.id, price=price)
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


@app.delete("/symbols/{ticker}", status_code=204)
def remove_symbol(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    db.delete(symbol)
    db.commit()


@app.get("/symbols/{ticker}/lots", response_model=list[PositionLotOut])
def list_lots(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    return (
        db.query(models.PositionLot)
        .filter_by(symbol_id=symbol.id)
        .order_by(models.PositionLot.purchased_at)
        .all()
    )


@app.post("/symbols/{ticker}/lots", response_model=PositionLotOut)
def add_lot(ticker: str, payload: PositionLotCreate, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    # Si el símbolo tenía una posición cargada a la antigua (un solo valor,
    # sin lotes todavía), la migramos a un lote implícito para no perderla.
    has_lots = db.query(models.PositionLot).filter_by(symbol_id=symbol.id).first() is not None
    if not has_lots and symbol.quantity and symbol.avg_cost:
        db.add(
            models.PositionLot(
                symbol_id=symbol.id,
                quantity=symbol.quantity,
                price=symbol.avg_cost,
                purchased_at=symbol.created_at,
            )
        )

    lot = models.PositionLot(
        symbol_id=symbol.id,
        quantity=payload.quantity,
        price=payload.price,
        purchased_at=payload.purchased_at or datetime.now(timezone.utc),
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)

    refresh_symbol_position(db, symbol)
    return lot


@app.patch("/symbols/{ticker}/lots/{lot_id}", response_model=PositionLotOut)
def update_lot(ticker: str, lot_id: int, payload: PositionLotUpdate, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    lot = db.query(models.PositionLot).filter_by(id=lot_id, symbol_id=symbol.id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    if payload.quantity is not None:
        lot.quantity = payload.quantity
    if payload.price is not None:
        lot.price = payload.price
    if payload.purchased_at is not None:
        lot.purchased_at = payload.purchased_at
    db.commit()
    db.refresh(lot)

    refresh_symbol_position(db, symbol)
    return lot


@app.delete("/symbols/{ticker}/lots/{lot_id}", status_code=204)
def remove_lot(ticker: str, lot_id: int, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    lot = db.query(models.PositionLot).filter_by(id=lot_id, symbol_id=symbol.id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    db.delete(lot)
    db.commit()
    refresh_symbol_position(db, symbol)


def _get_current_price(db, symbol) -> float:
    latest_point = (
        db.query(models.PricePoint)
        .filter_by(symbol_id=symbol.id)
        .order_by(desc(models.PricePoint.fetched_at))
        .first()
    )
    if latest_point:
        return latest_point.price
    return fetch_current_price(symbol.ticker)


def _compute_insights(db, symbol) -> InsightsOut:
    current_price = _get_current_price(db, symbol)
    sentiment = aggregate_sentiment(db, symbol.id)

    try:
        analyst = fetch_analyst_rating(symbol.ticker)
    except Exception:
        analyst = {"rating": "No data", "counts": None}

    targets = project_target_prices(db, symbol.id, current_price, sentiment["medium_term"])
    recommendations = generate_recommendations(current_price, symbol.quantity, targets)

    unrealized_pnl_pct = None
    if symbol.avg_cost:
        unrealized_pnl_pct = round((current_price - symbol.avg_cost) / symbol.avg_cost * 100, 2)

    ml_1d = predict_direction(db, symbol.id, symbol.ticker, "1d", current_price)
    ml_1w = predict_direction(db, symbol.id, symbol.ticker, "1w", current_price)

    try:
        fundamentals = fetch_fundamentals(symbol.ticker)
    except Exception:
        fundamentals = None

    eps_analysis = analyze_eps(fundamentals) if fundamentals else None

    return InsightsOut(
        sentiment_short_term=sentiment["short_term"],
        sentiment_medium_term=sentiment["medium_term"],
        sentiment_long_term=sentiment["long_term"],
        analyst_rating=analyst["rating"],
        analyst_counts=analyst["counts"],
        target_price_1w=targets["target_price_1w"],
        target_price_1m=targets["target_price_1m"],
        target_price_1y=targets["target_price_1y"],
        ml_direction_1d=ml_1d,
        ml_direction_1w=ml_1w,
        fundamentals=fundamentals,
        eps_analysis=eps_analysis,
        quantity=symbol.quantity,
        avg_cost=symbol.avg_cost,
        unrealized_pnl_pct=unrealized_pnl_pct,
        recommendation_1w=recommendations["1w"],
        recommendation_1m=recommendations["1m"],
        recommendation_1y=recommendations["1y"],
    )


@app.get("/symbols/{ticker}/insights", response_model=InsightsOut)
def get_insights(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    return _compute_insights(db, symbol)


ANALYSIS_MAX_AGE = timedelta(hours=12)


@app.get("/symbols/{ticker}/analysis", response_model=AiAnalysisOut)
def get_ai_analysis(ticker: str, refresh: bool = False, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    is_stale = (
        not symbol.ai_analysis
        or not symbol.ai_analysis_generated_at
        or datetime.now(timezone.utc) - symbol.ai_analysis_generated_at.replace(tzinfo=timezone.utc) > ANALYSIS_MAX_AGE
    )

    if is_stale or refresh:
        insight = _compute_insights(db, symbol)
        current_price = _get_current_price(db, symbol)
        stock_news = (
            db.query(models.NewsItem)
            .filter_by(symbol_id=symbol.id)
            .order_by(desc(models.NewsItem.published_at))
            .limit(6)
            .all()
        )
        general_symbol = db.query(models.Symbol).filter_by(ticker=GENERAL_TICKER).first()
        general_news = (
            db.query(models.NewsItem)
            .filter_by(symbol_id=general_symbol.id)
            .order_by(desc(models.NewsItem.published_at))
            .limit(4)
            .all()
            if general_symbol
            else []
        )
        headlines = [
            {
                "headline": n.headline,
                "topic": n.topic,
                "scope": n.scope,
                "impact_direction": n.impact_direction,
            }
            for n in [*stock_news, *general_news]
        ]
        try:
            text = generate_analysis(symbol.ticker, current_price, insight.model_dump(), headlines)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"No se pudo generar el análisis: {e}")

        symbol.ai_analysis = text
        symbol.ai_analysis_generated_at = datetime.now(timezone.utc)
        db.commit()

    return AiAnalysisOut(text=symbol.ai_analysis, generated_at=symbol.ai_analysis_generated_at)


@app.get("/symbols/{ticker}/news", response_model=list[NewsItemOut])
def get_news(ticker: str, db: Session = Depends(get_db)):
    symbol = db.query(models.Symbol).filter_by(ticker=ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not tracked")

    return (
        db.query(models.NewsItem)
        .filter_by(symbol_id=symbol.id)
        .order_by(desc(models.NewsItem.published_at))
        .limit(20)
        .all()
    )


@app.get("/market/news", response_model=list[NewsItemOut])
def get_general_market_news(db: Session = Depends(get_db)):
    general_symbol = db.query(models.Symbol).filter_by(ticker=GENERAL_TICKER).first()
    if not general_symbol:
        return []

    return (
        db.query(models.NewsItem)
        .filter_by(symbol_id=general_symbol.id)
        .order_by(desc(models.NewsItem.published_at))
        .limit(20)
        .all()
    )
