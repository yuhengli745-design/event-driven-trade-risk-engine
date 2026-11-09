"""Event dispatcher and aggregate state for the trading engine."""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from .events import (
    Event,
    ExecutionReceived,
    OrderCancelled,
    OrderStatus,
    OrderSubmitted,
    PriceUpdated,
)
from .models import Order, Position
from .risk import RiskManager


class EventSink(Protocol):
    def append(self, event: Event) -> None: ...


class EventSource(Protocol):
    def read_all(self) -> list[Event]: ...


class ProcessingStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    status: ProcessingStatus
    event_id: str
    reason: str = ""


class TradingEngine:
    def __init__(
        self,
        risk_manager: RiskManager,
        event_store: EventSink | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self.risk_manager = risk_manager
        self.event_store = event_store
        self.logger = logger
        self.orders: dict[str, Order] = {}
        self.positions: dict[str, Position] = {}
        self.prices: dict[str, Decimal] = {}
        self.execution_ids: set[str] = set()
        self.processed_event_ids: set[str] = set()

    def process(self, event: Event, *, persist: bool = True) -> ProcessingResult:
        candidate = self._candidate()
        result = candidate._apply(event)
        if persist and self.event_store is not None:
            self.event_store.append(event)
        self._commit(candidate)
        self._log(event, result)
        return result

    def replay(self, source: EventSource) -> list[ProcessingResult]:
        return [self.process(event, persist=False) for event in source.read_all()]

    def _candidate(self) -> TradingEngine:
        candidate = TradingEngine(self.risk_manager)
        candidate.orders = deepcopy(self.orders)
        candidate.positions = deepcopy(self.positions)
        candidate.prices = deepcopy(self.prices)
        candidate.execution_ids = set(self.execution_ids)
        candidate.processed_event_ids = set(self.processed_event_ids)
        return candidate

    def _commit(self, candidate: TradingEngine) -> None:
        self.orders = candidate.orders
        self.positions = candidate.positions
        self.prices = candidate.prices
        self.execution_ids = candidate.execution_ids
        self.processed_event_ids = candidate.processed_event_ids

    def _log(self, event: Event, result: ProcessingResult) -> None:
        if self.logger is None:
            return
        data = {
            "event_type": type(event).__name__,
            "event_id": event.event_id,
            "status": result.status.value,
        }
        for field in ("order_id", "execution_id", "symbol"):
            if hasattr(event, field):
                data[field] = getattr(event, field)
        if result.reason:
            data["reason"] = result.reason
        self.logger.info("event_processed", extra={"event_data": data})

    def _apply(self, event: Event) -> ProcessingResult:
        if event.event_id in self.processed_event_ids:
            return ProcessingResult(ProcessingStatus.IGNORED, event.event_id, "duplicate event_id")

        if isinstance(event, OrderSubmitted):
            result = self._submit(event)
        elif isinstance(event, OrderCancelled):
            result = self._cancel(event)
        elif isinstance(event, ExecutionReceived):
            result = self._execute(event)
        elif isinstance(event, PriceUpdated):
            result = self._price(event)
        else:  # pragma: no cover - closed event union, defensive at runtime
            raise TypeError(f"unsupported event type: {type(event).__name__}")

        self.processed_event_ids.add(event.event_id)
        return result

    def _submit(self, event: OrderSubmitted) -> ProcessingResult:
        if event.order_id in self.orders:
            return ProcessingResult(ProcessingStatus.REJECTED, event.event_id, "duplicate order_id")
        current = self.positions.get(event.symbol)
        risk = self.risk_manager.validate(
            event.symbol,
            event.side,
            event.quantity,
            event.limit_price,
            Decimal("0") if current is None else current.quantity,
            list(self.orders.values()),
        )
        order = Order(
            event.order_id,
            event.symbol,
            event.side,
            event.quantity,
            event.limit_price,
        )
        if not risk.approved:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = risk.reason
            self.orders[event.order_id] = order
            return ProcessingResult(ProcessingStatus.REJECTED, event.event_id, risk.reason)
        self.orders[event.order_id] = order
        return ProcessingResult(ProcessingStatus.ACCEPTED, event.event_id)

    def _cancel(self, event: OrderCancelled) -> ProcessingResult:
        order = self.orders.get(event.order_id)
        if order is None:
            return ProcessingResult(ProcessingStatus.REJECTED, event.event_id, "unknown order_id")
        if not order.is_active:
            return ProcessingResult(
                ProcessingStatus.REJECTED,
                event.event_id,
                f"cannot cancel order in {order.status.value} state",
            )
        order.status = OrderStatus.CANCELLED
        return ProcessingResult(ProcessingStatus.ACCEPTED, event.event_id)

    def _execute(self, event: ExecutionReceived) -> ProcessingResult:
        if event.execution_id in self.execution_ids:
            return ProcessingResult(
                ProcessingStatus.IGNORED, event.event_id, "duplicate execution_id"
            )
        order = self.orders.get(event.order_id)
        if order is None:
            return ProcessingResult(ProcessingStatus.REJECTED, event.event_id, "unknown order_id")
        try:
            order.apply_execution(event.quantity)
        except ValueError as exc:
            return ProcessingResult(ProcessingStatus.REJECTED, event.event_id, str(exc))

        position = self.positions.setdefault(order.symbol, Position(order.symbol))
        position.apply_execution(event.quantity * order.side.sign, event.price)
        if order.symbol in self.prices:
            position.mark(self.prices[order.symbol])
        self.execution_ids.add(event.execution_id)
        return ProcessingResult(ProcessingStatus.ACCEPTED, event.event_id)

    def _price(self, event: PriceUpdated) -> ProcessingResult:
        self.prices[event.symbol] = event.price
        if event.symbol in self.positions:
            self.positions[event.symbol].mark(event.price)
        return ProcessingResult(ProcessingStatus.ACCEPTED, event.event_id)

    def snapshot(self) -> dict[str, object]:
        return {
            "orders": {key: self.orders[key].snapshot() for key in sorted(self.orders)},
            "positions": {key: self.positions[key].snapshot() for key in sorted(self.positions)},
            "prices": {key: str(self.prices[key]) for key in sorted(self.prices)},
            "execution_ids": sorted(self.execution_ids),
            "processed_event_ids": sorted(self.processed_event_ids),
        }
