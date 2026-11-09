"""Mutable order and position state owned by the engine."""

from dataclasses import dataclass
from decimal import Decimal

from .events import OrderStatus, Side

ZERO = Decimal("0")


@dataclass(slots=True)
class Order:
    order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    limit_price: Decimal
    filled_quantity: Decimal = ZERO
    status: OrderStatus = OrderStatus.NEW
    rejection_reason: str | None = None

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}

    def apply_execution(self, quantity: Decimal) -> None:
        if not self.is_active:
            raise ValueError(f"order {self.order_id} is not active")
        if quantity <= ZERO:
            raise ValueError("execution quantity must be positive")
        if quantity > self.remaining_quantity:
            raise ValueError("execution quantity exceeds remaining order quantity")
        self.filled_quantity += quantity
        self.status = (
            OrderStatus.FILLED
            if self.filled_quantity == self.quantity
            else OrderStatus.PARTIALLY_FILLED
        )

    def snapshot(self) -> dict[str, str | None]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "limit_price": str(self.limit_price),
            "filled_quantity": str(self.filled_quantity),
            "remaining_quantity": str(self.remaining_quantity),
            "status": self.status.value,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: Decimal = ZERO
    average_cost: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    market_price: Decimal | None = None

    def apply_execution(self, signed_quantity: Decimal, price: Decimal) -> None:
        if signed_quantity == ZERO:
            raise ValueError("signed quantity cannot be zero")
        if price <= ZERO:
            raise ValueError("execution price must be positive")

        old_quantity = self.quantity
        new_quantity = old_quantity + signed_quantity
        same_direction = old_quantity == ZERO or (old_quantity > ZERO) == (signed_quantity > ZERO)

        if same_direction:
            old_notional = abs(old_quantity) * self.average_cost
            added_notional = abs(signed_quantity) * price
            self.average_cost = (old_notional + added_notional) / abs(new_quantity)
        else:
            closed_quantity = min(abs(old_quantity), abs(signed_quantity))
            direction = Decimal("1") if old_quantity > ZERO else Decimal("-1")
            self.realized_pnl += closed_quantity * (price - self.average_cost) * direction
            if new_quantity == ZERO:
                self.average_cost = ZERO
            elif (new_quantity > ZERO) != (old_quantity > ZERO):
                self.average_cost = price

        self.quantity = new_quantity

    def mark(self, price: Decimal) -> None:
        if price <= ZERO:
            raise ValueError("market price must be positive")
        self.market_price = price

    @property
    def unrealized_pnl(self) -> Decimal:
        if self.market_price is None:
            return ZERO
        return (self.market_price - self.average_cost) * self.quantity

    @property
    def total_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl

    def snapshot(self) -> dict[str, str | None]:
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "average_cost": str(self.average_cost),
            "realized_pnl": str(self.realized_pnl),
            "market_price": None if self.market_price is None else str(self.market_price),
            "unrealized_pnl": str(self.unrealized_pnl),
            "total_pnl": str(self.total_pnl),
        }
