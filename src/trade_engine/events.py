"""Immutable domain events accepted by the trading engine."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> Decimal:
        return Decimal("1") if self is Side.BUY else Decimal("-1")


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


def _require_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} cannot be blank")


def _validate_base(event_id: str, occurred_at: datetime) -> None:
    _require_text("event_id", event_id)
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")


def _require_positive(name: str, value: Decimal) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class OrderSubmitted:
    event_id: str
    occurred_at: datetime
    order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    limit_price: Decimal

    def __post_init__(self) -> None:
        _validate_base(self.event_id, self.occurred_at)
        _require_text("order_id", self.order_id)
        _require_text("symbol", self.symbol)
        _require_positive("quantity", self.quantity)
        _require_positive("limit_price", self.limit_price)


@dataclass(frozen=True, slots=True)
class OrderCancelled:
    event_id: str
    occurred_at: datetime
    order_id: str

    def __post_init__(self) -> None:
        _validate_base(self.event_id, self.occurred_at)
        _require_text("order_id", self.order_id)


@dataclass(frozen=True, slots=True)
class ExecutionReceived:
    event_id: str
    occurred_at: datetime
    execution_id: str
    order_id: str
    quantity: Decimal
    price: Decimal

    def __post_init__(self) -> None:
        _validate_base(self.event_id, self.occurred_at)
        _require_text("execution_id", self.execution_id)
        _require_text("order_id", self.order_id)
        _require_positive("quantity", self.quantity)
        _require_positive("price", self.price)


@dataclass(frozen=True, slots=True)
class PriceUpdated:
    event_id: str
    occurred_at: datetime
    symbol: str
    price: Decimal

    def __post_init__(self) -> None:
        _validate_base(self.event_id, self.occurred_at)
        _require_text("symbol", self.symbol)
        _require_positive("price", self.price)


Event = OrderSubmitted | OrderCancelled | ExecutionReceived | PriceUpdated
