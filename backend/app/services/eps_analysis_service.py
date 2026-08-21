"""
Clasificación de calidad del EPS según los criterios:
1. Crecimiento interanual del EPS: 10-25%/año en los últimos 3-5 años es la
   señal de "buen EPS" (no un valor nominal absoluto).
2. Contextualización con P/E: el EPS por sí solo no dice si la acción está
   cara o barata, hay que mirarlo junto al P/E.

Nota: no calculamos un "EPS Rating" al estilo IBD (0-100 vs. TODO el mercado)
porque esa calificación es propietaria de Investor's Business Daily y no hay
forma gratuita de replicarla con validez real — solo trackeamos un puñado de
símbolos, no el universo completo de acciones, así que un percentil calculado
contra tan pocos símbolos sería engañoso si se presentara como si fuera lo
mismo que el EPS Rating real.
"""


def _growth_label(growth: float | None) -> tuple[str, str]:
    if growth is None:
        return "Sin datos", "No hay dato de crecimiento de EPS disponible."
    if growth >= 25:
        return (
            "Muy alto",
            f"Crecimiento de EPS de {growth:.1f}%/año, por encima del rango típico de 10-25% — "
            "fuerte pero vale la pena revisar si es sostenible o un pico puntual.",
        )
    if growth >= 10:
        return (
            "Bueno",
            f"Crecimiento de EPS de {growth:.1f}%/año, dentro del rango de 10-25% considerado saludable — "
            "la empresa está generando cada vez más valor por acción de forma consistente.",
        )
    if growth >= 0:
        return (
            "Débil",
            f"Crecimiento de EPS de {growth:.1f}%/año, por debajo del 10% — señal de madurez o "
            "crecimiento lento, no necesariamente malo pero sin el impulso de una empresa en expansión.",
        )
    return (
        "Negativo",
        f"EPS cayendo ({growth:.1f}%/año) — señal de declive en la rentabilidad por acción, amerita revisar el motivo.",
    )


def analyze_eps(fundamentals: dict) -> dict:
    growth_5y = fundamentals.get("eps_growth_5y")
    growth_3y = fundamentals.get("eps_growth_3y")
    eps_ttm = fundamentals.get("eps_ttm")
    pe_ttm = fundamentals.get("pe_ttm")

    primary_growth = growth_5y if growth_5y is not None else growth_3y
    label, explanation = _growth_label(primary_growth)

    pe_context = None
    if eps_ttm is not None and pe_ttm is not None:
        pe_context = (
            f"EPS (TTM) de ${eps_ttm:.2f} con P/E de {pe_ttm:.1f}x — "
            f"el mercado está pagando {pe_ttm:.1f}x las ganancias anuales por acción."
        )

    return {
        "quality_label": label,
        "growth_explanation": explanation,
        "pe_context": pe_context,
        "eps_growth_3y": growth_3y,
        "eps_growth_5y": growth_5y,
        "eps_growth_ttm_yoy": fundamentals.get("eps_growth_ttm_yoy"),
        "eps_growth_quarterly_yoy": fundamentals.get("eps_growth_quarterly_yoy"),
    }
