from app import models


def aggregate_position(db, symbol_id: int) -> tuple[float | None, float | None]:
    lots = db.query(models.PositionLot).filter_by(symbol_id=symbol_id).all()
    if not lots:
        return None, None

    total_quantity = sum(lot.quantity for lot in lots)
    if total_quantity == 0:
        return 0.0, None

    weighted_cost = sum(lot.quantity * lot.price for lot in lots) / total_quantity
    return total_quantity, weighted_cost


def refresh_symbol_position(db, symbol: models.Symbol):
    quantity, avg_cost = aggregate_position(db, symbol.id)
    symbol.quantity = quantity
    symbol.avg_cost = avg_cost
    db.commit()
