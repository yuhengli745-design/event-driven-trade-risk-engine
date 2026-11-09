from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trade_engine.engine import TradingEngine
from trade_engine.event_store import EventStoreError, JsonLinesEventStore, decode_event, encode_event
from trade_engine.events import OrderSubmitted, Side
from trade_engine.risk import RiskLimits, RiskManager


NOW = datetime(2026, 6, 1, 12, 30, tzinfo=UTC)


def test_event_round_trip_preserves_decimal_and_timestamp() -> None:
    event = OrderSubmitted("e1", NOW, "o1", "AAPL", Side.BUY, Decimal("1.25"), Decimal("99.90"))
    assert decode_event(encode_event(event)) == event


def test_store_preserves_append_order(tmp_path) -> None:
    store = JsonLinesEventStore(tmp_path / "events.jsonl")
    first = OrderSubmitted("e1", NOW, "o1", "AAPL", Side.BUY, Decimal("1"), Decimal("10"))
    second = OrderSubmitted("e2", NOW, "o2", "MSFT", Side.SELL, Decimal("2"), Decimal("20"))
    store.append(first)
    store.append(second)
    assert store.read_all() == [first, second]


@pytest.mark.parametrize(
    "line",
    ["not-json", '{"schema_version":1,"event_type":"Unknown","payload":{}}'],
)
def test_malformed_records_report_line_number(tmp_path, line: str) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(EventStoreError, match="line 1"):
        JsonLinesEventStore(path).read_all()


def test_append_failure_leaves_engine_state_unchanged() -> None:
    class BrokenStore:
        def append(self, event) -> None:
            raise EventStoreError("disk full")

    subject = TradingEngine(RiskManager(RiskLimits(Decimal("100"), Decimal("10000"))), BrokenStore())
    event = OrderSubmitted("e1", NOW, "o1", "AAPL", Side.BUY, Decimal("1"), Decimal("10"))
    with pytest.raises(EventStoreError, match="disk full"):
        subject.process(event)
    assert subject.orders == {}
    assert subject.processed_event_ids == set()
