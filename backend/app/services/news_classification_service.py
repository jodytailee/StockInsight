"""
Clasifica noticias nuevas en lote usando Claude: tema, alcance (mercado
general vs. específico de la empresa), y una predicción de impacto
direccional. Se llama en lotes (no una request por noticia) para no disparar
el costo/latencia de la API.
"""

import json

import requests

from app.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"
BATCH_SIZE = 20

TOPICS = [
    "earnings",
    "macro_rates",
    "geopolitics",
    "regulation",
    "supply_chain",
    "product",
    "m_and_a",
    "leadership",
    "market_sentiment",
    "other",
]


def _build_prompt(items: list[dict]) -> str:
    numbered = "\n".join(f"{i}. [{it['ticker']}] {it['headline']}" for i, it in enumerate(items))
    topics_str = ", ".join(TOPICS)
    return f"""Clasificá cada uno de estos titulares financieros. Para cada uno devolvé:
- "topic": uno de estos valores exactos: {topics_str}
- "scope": "market_wide" si la noticia afecta al mercado en general o a un sector amplio (tasas de interés, geopolítica, inflación, etc.), o "stock_specific" si es específica de esa empresa (earnings, producto, management, M&A de esa empresa)
- "impact_direction": "up", "down", o "neutral" — tu mejor estimación de hacia dónde empuja el precio de la acción esta noticia

Titulares (formato: índice. [TICKER] titular):
{numbered}

Respondé ÚNICAMENTE con un array JSON, un objeto por titular, en el mismo orden, con este formato exacto:
[{{"topic": "...", "scope": "...", "impact_direction": "..."}}, ...]

Sin texto adicional, sin markdown, solo el array JSON."""


def _call_claude(prompt: str) -> list[dict]:
    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 2000,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text_blocks = [b["text"] for b in data["content"] if b.get("type") == "text"]
    if not text_blocks:
        raise ValueError(f"Respuesta de Anthropic sin bloque de texto: {data}")
    text = "".join(text_blocks).strip()
    # Por si el modelo envuelve la respuesta en ```json ... ```
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def classify_batch(items: list[dict]) -> list[dict]:
    """items: [{"ticker": str, "headline": str}, ...]. Devuelve una lista del
    mismo largo con {"topic", "scope", "impact_direction"} por ítem, o valores
    None si falla la clasificación (no bloquea el guardado de la noticia)."""
    if not items or not settings.anthropic_api_key:
        return [None] * len(items)

    results: list[dict | None] = []
    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start : start + BATCH_SIZE]
        try:
            prompt = _build_prompt(chunk)
            parsed = _call_claude(prompt)
            if len(parsed) != len(chunk):
                raise ValueError(f"esperaba {len(chunk)} resultados, llegaron {len(parsed)}")
            results.extend(parsed)
        except Exception as e:
            print(f"[news_classification] fallo clasificando lote de {len(chunk)}: {e}")
            results.extend([None] * len(chunk))
    return results
