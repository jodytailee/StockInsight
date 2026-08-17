from datetime import datetime, timedelta, timezone

from app import models
from app.ml.predict import predict_direction

NEWS_WINDOW = timedelta(days=1)


def _sentiment_word(score: float) -> str:
    if score > 0.2:
        return "Positiva"
    if score < -0.2:
        return "Negativa"
    return "Neutral"


def _symbol_section_html(db, symbol: models.Symbol) -> str:
    since = datetime.now(timezone.utc) - NEWS_WINDOW
    news_items = (
        db.query(models.NewsItem)
        .filter(models.NewsItem.symbol_id == symbol.id, models.NewsItem.published_at >= since)
        .order_by(models.NewsItem.published_at.desc())
        .all()
    )

    latest_point = (
        db.query(models.PricePoint)
        .filter_by(symbol_id=symbol.id)
        .order_by(models.PricePoint.fetched_at.desc())
        .first()
    )
    current_price = latest_point.price if latest_point else None

    ml_1d = predict_direction(db, symbol.id, symbol.ticker, "1d", current_price)
    ml_1w = predict_direction(db, symbol.id, symbol.ticker, "1w", current_price)

    def ml_line(label: str, ml: dict | None) -> str:
        if not ml:
            return f"<li>{label}: sin modelo entrenado todavía</li>"
        acc = f"{ml['test_accuracy'] * 100:.0f}%" if ml["test_accuracy"] is not None else "N/D"
        return (
            f"<li>{label}: {ml['probability_up'] * 100:.0f}% probabilidad de subir "
            f"(accuracy histórico del modelo: {acc}, entrenado {ml['trained_at'][:10]})</li>"
        )

    news_html = "<p style='color:#888'>Sin noticias nuevas en las últimas 24h.</p>"
    if news_items:
        rows = "".join(
            f"<li><a href='{n.url}'>{n.headline}</a> — {n.source}, "
            f"sentimiento: {_sentiment_word(n.sentiment_score)}</li>"
            for n in news_items
        )
        news_html = f"<ul>{rows}</ul>"

    price_html = f"${current_price:.2f}" if current_price is not None else "N/D"

    return f"""
    <h2>{symbol.ticker}</h2>
    <p>Precio actual: {price_html}</p>
    <h3>Noticias (últimas 24h) — {len(news_items)}</h3>
    {news_html}
    <h3>Estado del modelo ML</h3>
    <ul>
        {ml_line("1 día", ml_1d)}
        {ml_line("1 semana", ml_1w)}
    </ul>
    <hr />
    """


def build_daily_digest_html(db) -> str:
    symbols = db.query(models.Symbol).all()
    if not symbols:
        return "<p>No hay símbolos trackeados todavía.</p>"

    sections = "".join(_symbol_section_html(db, s) for s in symbols)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""
    <h1>StockInsight — Resumen diario ({today})</h1>
    <p style="color:#888">
        Recordatorio: los modelos ML son experimentales (accuracy histórico bajo),
        y las proyecciones de precio/recomendaciones son una heurística preliminar,
        no asesoría financiera.
    </p>
    {sections}
    """
