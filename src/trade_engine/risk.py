"""Pre-trade position and notional risk controls."""

from dataclasses import dataclass
from decimal import Decimal

from .events import Side
from .models import Order


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_abs_position: Decimal
    max_abs_notional: Decimal

    def __post_init__(self) -> None:
        if self.max_abs_position <= 0 or self.max_abs_notional <= 0:
            raise ValueError("risk limits must be positive")


@dataclass(frozen=True, slots=True)
class RiskResult:
    approved: bool
    projected_position: Decimal
    projected_notional: Decimal
    reason: str = ""


class RiskManager:
    def __init__(
        self,
        default_limits: RiskLimits,
        symbol_limits: dict[str, RiskLimits] | None = None,
    ) -> None:
        self.default_limits = default_limits
        self.symbol_limits = symbol_limits or {}

    def validate(
        self,
        symbol: str,
        side: Side,
        quantity: Decimal,
        limit_price: Decimal,
        current_position: Decimal,
        open_orders: list[Order],
    ) -> RiskResult:
        reserved = sum(
            (
                order.remaining_quantity * order.side.sign
                for order in open_orders
                if order.symbol == symbol and order.is_active
            ),
            start=Decimal("0"),
        )
        projected = current_position + reserved + quantity * side.sign
        projected_notional = abs(projected * limit_price)
        limits = self.symbol_limits.get(symbol, self.default_limits)
        if abs(projected) > limits.max_abs_position:
            return RiskResult(
                False,
                projected,
                projected_notional,
                f"projected position {projected} exceeds limit {limits.max_abs_position}",
            )
        if projected_notional > limits.max_abs_notional:
            return RiskResult(
                False,
                projected,
                projected_notional,
                f"projected notional {projected_notional} exceeds limit {limits.max_abs_notional}",
            )
        return RiskResult(True, projected, projected_notional)
