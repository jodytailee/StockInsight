"""
Recomendaciones de compra/venta por horizonte, basadas en el target price
preliminar (app/services/projection_service.py) y en si el usuario ya tiene
posición en el símbolo. Igual que el target price, esto es una heurística
simple — no el modelo ML — hasta que haya suficiente histórico propio.
"""

# % de movimiento esperado a partir del cual se recomienda actuar, por horizonte.
BUY_THRESHOLD = {"1w": 0.03, "1m": 0.05, "1y": 0.10}
SELL_THRESHOLD = {"1w": -0.03, "1m": -0.05, "1y": -0.10}


def _action_for(expected_return: float, horizon: str, holds_position: bool) -> str:
    if expected_return >= BUY_THRESHOLD[horizon]:
        return "Comprar más" if holds_position else "Comprar"
    if expected_return <= SELL_THRESHOLD[horizon]:
        return "Vender" if holds_position else "Evitar"
    return "Mantener" if holds_position else "Neutral"


def generate_recommendations(current_price: float, quantity: float | None, targets: dict) -> dict:
    holds_position = bool(quantity and quantity > 0)
    horizon_targets = {
        "1w": targets["target_price_1w"],
        "1m": targets["target_price_1m"],
        "1y": targets["target_price_1y"],
    }

    recommendations = {}
    for horizon, target_price in horizon_targets.items():
        expected_return = (target_price - current_price) / current_price
        recommendations[horizon] = {
            "action": _action_for(expected_return, horizon, holds_position),
            "expected_return_pct": round(expected_return * 100, 2),
        }
    return recommendations
