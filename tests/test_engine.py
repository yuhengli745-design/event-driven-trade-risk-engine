from datetime import UTC, datetime
from decimal import Decimal

from trade_engine.engine import ProcessingStatus, TradingEngine
from trade_engine.events import (
    ExecutionReceived,
    OrderCancelled,
    OrderSubmitted,
    PriceUpdated,
    Side,
)
from trade_engine.risk import RiskLimits, RiskManager

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def engine() -> TradingEngine:
    return TradingEngine(RiskManager(RiskLimits(Decimal("100"), Decimal("10000"))))


def order(
    event_id: str = "e1", order_id: str = "o1", quantity: str = "10", price: str = "100"
) -> OrderSubmitted:
    return OrderSubmitted(
        event_id, NOW, order_id, "AAPL", Side.BUY, Decimal(quantity), Decimal(price)
    )


def test_submit_fill_price_and_cancel_lifecycle() -> None:
    subject = engine()
    assert subject.process(order()).status is ProcessingStatus.ACCEPTED
    assert (
        subject.process(
            ExecutionReceived("e2", NOW, "x1", "o1", Decimal("4"), Decimal("99"))
        ).status
        is ProcessingStatus.ACCEPTED
    )
    subject.process(PriceUpdated("e3", NOW, "AAPL", Decimal("101")))
    assert subject.positions["AAPL"].unrealized_pnl == Decimal("8")
    assert subject.process(OrderCancelled("e4", NOW, "o1")).status is ProcessingStatus.ACCEPTED


def test_risk_rejection_creates_rejected_order() -> None:
    subject = engine()
    result = subject.process(order(quantity="101", price="1"))
    assert result.status is ProcessingStatus.REJECTED
    assert subject.orders["o1"].status.value == "REJECTED"


def test_invalid_lifecycle_and_missing_order_are_rejected() -> None:
    subject = engine()
    assert subject.process(OrderCancelled("e1", NOW, "missing")).status is ProcessingStatus.REJECTED
    subject.process(order("e2"))
    subject.process(OrderCancelled("e3", NOW, "o1"))
    result = subject.process(ExecutionReceived("e4", NOW, "x1", "o1", Decimal("1"), Decimal("100")))
    assert result.status is ProcessingStatus.REJECTED


def test_duplicate_execution_is_ignored_even_if_payload_differs() -> None:
    subject = engine()
    subject.process(order())
    first = ExecutionReceived("e2", NOW, "x1", "o1", Decimal("4"), Decimal("100"))
    duplicate = ExecutionReceived("e3", NOW, "x1", "o1", Decimal("9"), Decimal("1"))
    assert subject.process(first).status is ProcessingStatus.ACCEPTED
    assert subject.process(duplicate).status is ProcessingStatus.IGNORED
    assert subject.orders["o1"].filled_quantity == Decimal("4")
    assert subject.positions["AAPL"].quantity == Decimal("4")


def test_overfill_rejection_is_atomic() -> None:
    subject = engine()
    subject.process(order())
    before = subject.snapshot()
    result = subject.process(
        ExecutionReceived("e2", NOW, "x1", "o1", Decimal("11"), Decimal("100"))
    )
    assert result.status is ProcessingStatus.REJECTED
    assert subject.orders["o1"].filled_quantity == Decimal("0")
    assert "AAPL" not in subject.positions
    assert before["orders"] == subject.snapshot()["orders"]


def test_duplicate_order_and_event_ids_are_rejected_or_ignored() -> None:
    subject = engine()
    subject.process(order())
    assert subject.process(order("e2")).status is ProcessingStatus.REJECTED
    assert (
        subject.process(PriceUpdated("e1", NOW, "AAPL", Decimal("1"))).status
        is ProcessingStatus.IGNORED
    )
