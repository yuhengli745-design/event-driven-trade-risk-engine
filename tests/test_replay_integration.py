from datetime import UTC, datetime
from decimal import Decimal

from trade_engine.engine import ProcessingStatus, TradingEngine
from trade_engine.event_store import JsonLinesEventStore
from trade_engine.events import ExecutionReceived, OrderSubmitted, PriceUpdated, Side
from trade_engine.risk import RiskLimits, RiskManager

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def make_engine(store=None) -> TradingEngine:
    return TradingEngine(RiskManager(RiskLimits(Decimal("100"), Decimal("10000"))), store)


def test_replay_reproduces_state_with_rejected_and_ignored_events(tmp_path) -> None:
    store = JsonLinesEventStore(tmp_path / "events.jsonl")
    live = make_engine(store)
    events = [
        OrderSubmitted("e1", NOW, "o1", "AAPL", Side.BUY, Decimal("10"), Decimal("100")),
        ExecutionReceived("e2", NOW, "x1", "o1", Decimal("4"), Decimal("99")),
        ExecutionReceived("e3", NOW, "x1", "o1", Decimal("7"), Decimal("1")),
        OrderSubmitted("e4", NOW, "o2", "AAPL", Side.BUY, Decimal("1000"), Decimal("1")),
        PriceUpdated("e5", NOW, "AAPL", Decimal("105")),
    ]
    statuses = [live.process(event).status for event in events]
    assert statuses == [
        ProcessingStatus.ACCEPTED,
        ProcessingStatus.ACCEPTED,
        ProcessingStatus.IGNORED,
        ProcessingStatus.REJECTED,
        ProcessingStatus.ACCEPTED,
    ]

    replayed = make_engine()
    replayed.replay(store)
    assert replayed.snapshot() == live.snapshot()
    assert len(store.read_all()) == len(events)
