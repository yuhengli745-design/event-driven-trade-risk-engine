from datetime import UTC, datetime
from decimal import Decimal

from trade_engine.engine import ProcessingStatus, TradingEngine
from trade_engine.events import ExecutionReceived, OrderSubmitted, PriceUpdated, Side
from trade_engine.risk import RiskLimits, RiskManager


def test_complete_long_and_sell_workflow_calculates_pnl() -> None:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    engine = TradingEngine(RiskManager(RiskLimits(Decimal("100"), Decimal("50000"))))
    events = [
        OrderSubmitted("e1", now, "buy", "AAPL", Side.BUY, Decimal("10"), Decimal("100")),
        ExecutionReceived("e2", now, "x1", "buy", Decimal("10"), Decimal("100")),
        PriceUpdated("e3", now, "AAPL", Decimal("110")),
        OrderSubmitted("e4", now, "sell", "AAPL", Side.SELL, Decimal("4"), Decimal("110")),
        ExecutionReceived("e5", now, "x2", "sell", Decimal("4"), Decimal("110")),
    ]
    assert all(engine.process(event).status is ProcessingStatus.ACCEPTED for event in events)
    position = engine.positions["AAPL"]
    assert position.quantity == Decimal("6")
    assert position.realized_pnl == Decimal("40")
    assert position.unrealized_pnl == Decimal("60")
    assert position.total_pnl == Decimal("100")
