"""Versioned JSON Lines event serialization and append-only storage."""

from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .events import Event, ExecutionReceived, OrderCancelled, OrderSubmitted, PriceUpdated, Side

SCHEMA_VERSION = 1


class EventStoreError(RuntimeError):
    """Raised when an event cannot be serialized, persisted, or decoded."""


def _payload(event: Event) -> dict[str, str]:
    common = {"event_id": event.event_id, "occurred_at": event.occurred_at.isoformat()}
    if isinstance(event, OrderSubmitted):
        return common | {
            "order_id": event.order_id,
            "symbol": event.symbol,
            "side": event.side.value,
            "quantity": str(event.quantity),
            "limit_price": str(event.limit_price),
        }
    if isinstance(event, OrderCancelled):
        return common | {"order_id": event.order_id}
    if isinstance(event, ExecutionReceived):
        return common | {
            "execution_id": event.execution_id,
            "order_id": event.order_id,
            "quantity": str(event.quantity),
            "price": str(event.price),
        }
    if isinstance(event, PriceUpdated):
        return common | {"symbol": event.symbol, "price": str(event.price)}
    raise EventStoreError(f"unsupported event type: {type(event).__name__}")


def encode_event(event: Event) -> str:
    record = {
        "event_type": type(event).__name__,
        "payload": _payload(event),
        "schema_version": SCHEMA_VERSION,
    }
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def decode_event(raw: str) -> Event:
    try:
        record: Any = json.loads(raw)
        if not isinstance(record, dict):
            raise EventStoreError("event record must be a JSON object")
        if record.get("schema_version") != SCHEMA_VERSION:
            raise EventStoreError(f"unsupported schema version: {record.get('schema_version')}")
        event_type = record["event_type"]
        payload = record["payload"]
        base = (payload["event_id"], datetime.fromisoformat(payload["occurred_at"]))
        if event_type == "OrderSubmitted":
            return OrderSubmitted(
                *base,
                payload["order_id"],
                payload["symbol"],
                Side(payload["side"]),
                Decimal(payload["quantity"]),
                Decimal(payload["limit_price"]),
            )
        if event_type == "OrderCancelled":
            return OrderCancelled(*base, payload["order_id"])
        if event_type == "ExecutionReceived":
            return ExecutionReceived(
                *base,
                payload["execution_id"],
                payload["order_id"],
                Decimal(payload["quantity"]),
                Decimal(payload["price"]),
            )
        if event_type == "PriceUpdated":
            return PriceUpdated(*base, payload["symbol"], Decimal(payload["price"]))
        raise EventStoreError(f"unknown event type: {event_type}")
    except EventStoreError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise EventStoreError(f"invalid event record: {exc}") from exc


class JsonLinesEventStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, event: Event) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encode_event(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise EventStoreError(f"could not append event: {exc}") from exc

    def read_all(self) -> list[Event]:
        if not self.path.exists():
            return []
        events: list[Event] = []
        try:
            with self.path.open(encoding="utf-8") as handle:
                for line_number, raw in enumerate(handle, start=1):
                    try:
                        if not raw.strip():
                            raise EventStoreError("blank record")
                        events.append(decode_event(raw))
                    except EventStoreError as exc:
                        raise EventStoreError(f"line {line_number}: {exc}") from exc
        except OSError as exc:
            raise EventStoreError(f"could not read event store: {exc}") from exc
        return events
