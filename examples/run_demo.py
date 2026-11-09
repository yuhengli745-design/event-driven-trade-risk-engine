"""Run a synthetic trade lifecycle, risk, idempotency, and replay demonstration."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trade_engine.engine import TradingEngine
from trade_engine.event_store import JsonLinesEventStore
from trade_engine.events import ExecutionReceived, OrderSubmitted, PriceUpdated, Side
from trade_engine.logging import configure_json_logger
from trade_engine.risk import RiskLimits, RiskManager


def build_engine(store: JsonLinesEventStore | None = None) -> TradingEngine:
    limits = RiskLimits(max_abs_position=Decimal("100"), max_abs_notional=Decimal("50000"))
    return TradingEngine(RiskManager(limits), store, logger=configure_json_logger())


def main() -> None:
    event_path = Path("demo-events.jsonl")
    event_path.unlink(missing_ok=True)
    store = JsonLinesEventStore(event_path)
    engine = build_engine(store)
    now = datetime(2026, 6, 1, 9, 30, tzinfo=UTC)
    events = [
        OrderSubmitted("evt-1", now, "buy-1", "AAPL", Side.BUY, Decimal("10"), Decimal("100")),
        ExecutionReceived("evt-2", now, "exec-1", "buy-1", Decimal("4"), Decimal("99")),
        ExecutionReceived("evt-3", now, "exec-1", "buy-1", Decimal("4"), Decimal("99")),
        ExecutionReceived("evt-4", now, "exec-2", "buy-1", Decimal("6"), Decimal("101")),
        PriceUpdated("evt-5", now, "AAPL", Decimal("105")),
        OrderSubmitted("evt-6", now, "too-large", "AAPL", Side.BUY, Decimal("1000"), Decimal("1")),
    ]
    for event in events:
        engine.process(event)

    print("\nFinal live state:")
    print(engine.snapshot())
    replayed = build_engine()
    replayed.replay(store)
    print(f"\nReplay matches live state: {replayed.snapshot() == engine.snapshot()}")


if __name__ == "__main__":
    main()
