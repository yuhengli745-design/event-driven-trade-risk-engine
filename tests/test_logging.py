import io
import json
from datetime import UTC, datetime
from decimal import Decimal

from trade_engine.engine import TradingEngine
from trade_engine.events import ExecutionReceived, OrderSubmitted, Side
from trade_engine.logging import configure_json_logger
from trade_engine.risk import RiskLimits, RiskManager

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def test_logs_accepted_rejected_and_ignored_results_as_json() -> None:
    stream = io.StringIO()
    logger = configure_json_logger(stream=stream, name="test-trade-engine")
    engine = TradingEngine(RiskManager(RiskLimits(Decimal("10"), Decimal("1000"))), logger=logger)
    engine.process(OrderSubmitted("e1", NOW, "o1", "AAPL", Side.BUY, Decimal("2"), Decimal("100")))
    engine.process(ExecutionReceived("e2", NOW, "x1", "o1", Decimal("1"), Decimal("100")))
    engine.process(ExecutionReceived("e3", NOW, "x1", "o1", Decimal("1"), Decimal("100")))
    engine.process(OrderSubmitted("e4", NOW, "o2", "AAPL", Side.BUY, Decimal("20"), Decimal("1")))

    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [record["status"] for record in records] == [
        "ACCEPTED",
        "ACCEPTED",
        "IGNORED",
        "REJECTED",
    ]
    assert records[2]["reason"] == "duplicate execution_id"
    assert records[1]["execution_id"] == "x1"
