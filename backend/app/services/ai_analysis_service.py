import requests

from app.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"


def _build_prompt(ticker: str, current_price: float, insight_data: dict, recent_headlines: list[str]) -> str:
    position_line = "Sin posición registrada."
    if insight_data.get("quantity") and insight_data.get("avg_cost"):
        position_line = (
            f"Posición actual: {insight_data['quantity']} acciones compradas a un promedio de "
            f"${insight_data['avg_cost']:.2f} (P&L no realizado: {insight_data.get('unrealized_pnl_pct')}%)."
        )

    ml_1d = insight_data.get("ml_direction_1d")
    ml_1w = insight_data.get("ml_direction_1w")
    ml_line = "Sin modelo ML entrenado todavía para este símbolo."
    if ml_1d or ml_1w:
        parts = []
        if ml_1d:
            parts.append(f"1 día: {ml_1d['probability_up'] * 100:.0f}% prob. de subir (accuracy histórico {ml_1d['test_accuracy'] * 100:.0f}%)")
        if ml_1w:
            parts.append(f"1 semana: {ml_1w['probability_up'] * 100:.0f}% prob. de subir (accuracy histórico {ml_1w['test_accuracy'] * 100:.0f}%)")
        ml_line = "Modelo ML (RandomForest sobre indicadores técnicos): " + "; ".join(parts)

    headlines_block = "\n".join(f"- {h}" for h in recent_headlines[:8]) or "Sin noticias recientes."

    fundamentals = insight_data.get("fundamentals")
    fundamentals_line = "Sin datos fundamentales disponibles."
    if fundamentals:
        fundamentals_line = (
            f"P/E (TTM): {fundamentals.get('pe_ttm')}, P/E forward: {fundamentals.get('forward_pe')}, "
            f"PEG: {fundamentals.get('peg_ttm')}, EPS (TTM): {fundamentals.get('eps_ttm')}, "
            f"Cash flow por acción (TTM): {fundamentals.get('cash_flow_per_share_ttm')}, "
            f"Margen bruto: {fundamentals.get('gross_margin_ttm')}%, Margen neto: {fundamentals.get('net_profit_margin_ttm')}%, "
            f"ROE: {fundamentals.get('roe_ttm')}%, ROA: {fundamentals.get('roa_ttm')}%, "
            f"Deuda/Equity: {fundamentals.get('debt_to_equity')}, Dividend yield: {fundamentals.get('dividend_yield_ttm')}%, "
            f"Beta: {fundamentals.get('beta')}, Market cap: ${fundamentals.get('market_cap')}M, "
            f"Rango 52 semanas: ${fundamentals.get('week52_low')} - ${fundamentals.get('week52_high')}, "
            f"Industria: {fundamentals.get('industry')}, "
            f"Crecimiento EPS 3Y: {fundamentals.get('eps_growth_3y')}%, 5Y: {fundamentals.get('eps_growth_5y')}%, "
            f"TTM YoY: {fundamentals.get('eps_growth_ttm_yoy')}%"
        )

    return f"""Sos un analista financiero generando un resumen breve para un dashboard personal de inversión (StockInsight). Analiza el símbolo {ticker}.

Datos disponibles:
- Precio actual: ${current_price:.2f}
- {position_line}
- Calificación de analistas (Finnhub): {insight_data.get('analyst_rating')}
- Sentimiento de noticias (VADER, -1 a +1): corto plazo {insight_data.get('sentiment_short_term')}, medio plazo {insight_data.get('sentiment_medium_term')}, largo plazo {insight_data.get('sentiment_long_term')}
- Target price preliminar (heurística, no ML): 1 semana ${insight_data.get('target_price_1w')}, 1 mes ${insight_data.get('target_price_1m')}, 1 año ${insight_data.get('target_price_1y')}
- {ml_line}
- Fundamentales (Finnhub): {fundamentals_line}
- Recomendación del sistema a 1 semana: {insight_data.get('recommendation_1w', {}).get('action')}

Titulares recientes:
{headlines_block}

Escribí un análisis de 4-5 oraciones en español, incorporando también una lectura de los fundamentales (¿la valuación por P/E parece cara o barata para la industria? ¿el cash flow y los márgenes son sanos? ¿el nivel de deuda es preocupante? ¿el crecimiento de EPS está en el rango saludable de 10-25% anual, estancado, o negativo?), explicando el razonamiento detrás de la recomendación actual, mencionando qué señales apuntan en qué dirección y si hay contradicciones entre ellas (ej. analistas positivos pero sentimiento de noticias negativo, o buen momentum pero fundamentales débiles). Sé directo y concreto, sin relleno. Terminá SIEMPRE con una frase aclarando que esto es informativo, generado automáticamente, y no es asesoría financiera profesional."""


def generate_analysis(ticker: str, current_price: float, insight_data: dict, recent_headlines: list[str]) -> str:
    prompt = _build_prompt(ticker, current_price, insight_data, recent_headlines)

    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 1000,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    text_blocks = [block["text"] for block in data["content"] if block.get("type") == "text"]
    if not text_blocks:
        raise ValueError(f"Respuesta de Anthropic sin bloque de texto: {data}")
    return "".join(text_blocks)
