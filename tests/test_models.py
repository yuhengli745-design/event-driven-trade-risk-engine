from decimal import Decimal

import pytest

from trade_engine.events import OrderStatus, Side
from trade_engine.models import Order, Position


def test_order_moves_from_partial_to_filled() -> None:
    order = Order("o1", "AAPL", Side.BUY, Decimal("10"), Decimal("100"))
    order.apply_execution(Decimal("4"))
    assert (order.filled_quantity, order.remaining_quantity, order.status) == (
        Decimal("4"),
        Decimal("6"),
        OrderStatus.PARTIALLY_FILLED,
    )
    order.apply_execution(Decimal("6"))
    assert order.status is OrderStatus.FILLED


def test_order_rejects_overfill_without_mutation() -> None:
    order = Order("o1", "AAPL", Side.BUY, Decimal("10"), Decimal("100"))
    with pytest.raises(ValueError, match="exceeds"):
        order.apply_execution(Decimal("11"))
    assert order.filled_quantity == 0


def test_long_position_weighted_cost_reduction_and_mark() -> None:
    position = Position("AAPL")
    position.apply_execution(Decimal("10"), Decimal("100"))
    position.apply_execution(Decimal("10"), Decimal("120"))
    position.apply_execution(Decimal("-5"), Decimal("130"))
    position.mark(Decimal("125"))
    assert position.quantity == Decimal("15")
    assert position.average_cost == Decimal("110")
    assert position.realized_pnl == Decimal("100")
    assert position.unrealized_pnl == Decimal("225")


def test_short_position_and_crossing_zero() -> None:
    position = Position("AAPL")
    position.apply_execution(Decimal("-10"), Decimal("100"))
    position.apply_execution(Decimal("15"), Decimal("90"))
    assert position.quantity == Decimal("5")
    assert position.average_cost == Decimal("90")
    assert position.realized_pnl == Decimal("100")


def test_closing_position_resets_average_cost() -> None:
    position = Position("AAPL")
    position.apply_execution(Decimal("10"), Decimal("100"))
    position.apply_execution(Decimal("-10"), Decimal("110"))
    assert position.quantity == Decimal("0")
    assert position.average_cost == Decimal("0")
    assert position.realized_pnl == Decimal("100")


def test_unrealized_pnl_is_zero_before_mark() -> None:
    position = Position("AAPL")
    position.apply_execution(Decimal("2"), Decimal("10"))
    assert position.unrealized_pnl == 0
