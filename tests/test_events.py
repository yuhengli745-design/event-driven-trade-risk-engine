from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trade_engine.events import (
    ExecutionReceived,
    OrderCancelled,
    OrderSubmitted,
    PriceUpdated,
    Side,
)


NOW = datetime(2026, 6, 1, tzinfo=UTC)


def test_order_submission_is_immutable_and_uses_decimal_values() -> None:
    event = OrderSubmitted("evt-1", NOW, "ord-1", "AAPL", Side.BUY, Decimal("10"), Decimal("185.50"))
    assert event.quantity == Decimal("10")
    with pytest.raises(FrozenInstanceError):
        event.symbol = "MSFT"  # type: ignore[misc]


@pytest.mark.parametrize("quantity,price", [("0", "10"), ("1", "0"), ("-1", "10")])
def test_order_submission_rejects_non_positive_values(quantity: str, price: str) -> None:
    with pytest.raises(ValueError):
        OrderSubmitted("evt", NOW, "ord", "AAPL", Side.BUY, Decimal(quantity), Decimal(price))


def test_events_require_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PriceUpdated("evt", datetime(2026, 1, 1), "AAPL", Decimal("10"))


def test_execution_and_price_require_positive_values() -> None:
    with pytest.raises(ValueError):
        ExecutionReceived("evt", NOW, "exe", "ord", Decimal("0"), Decimal("10"))
    with pytest.raises(ValueError):
        PriceUpdated("evt", NOW, "AAPL", Decimal("0"))


def test_identifiers_cannot_be_blank() -> None:
    with pytest.raises(ValueError):
        OrderCancelled("", NOW, "ord")
