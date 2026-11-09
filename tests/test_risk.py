from decimal import Decimal

from trade_engine.events import Side
from trade_engine.models import Order
from trade_engine.risk import RiskLimits, RiskManager


LIMITS = RiskLimits(Decimal("100"), Decimal("10000"))


def test_exact_risk_boundaries_are_approved() -> None:
    result = RiskManager(LIMITS).validate("AAPL", Side.BUY, Decimal("100"), Decimal("100"), Decimal("0"), [])
    assert result.approved
    assert result.projected_position == Decimal("100")


def test_position_limit_breach_is_rejected() -> None:
    result = RiskManager(LIMITS).validate("AAPL", Side.BUY, Decimal("101"), Decimal("1"), Decimal("0"), [])
    assert not result.approved
    assert "position" in result.reason


def test_notional_limit_breach_is_rejected() -> None:
    result = RiskManager(LIMITS).validate("AAPL", Side.BUY, Decimal("51"), Decimal("200"), Decimal("0"), [])
    assert not result.approved
    assert "notional" in result.reason


def test_active_orders_reserve_remaining_quantity() -> None:
    open_order = Order("old", "AAPL", Side.BUY, Decimal("60"), Decimal("100"))
    result = RiskManager(LIMITS).validate("AAPL", Side.BUY, Decimal("50"), Decimal("50"), Decimal("0"), [open_order])
    assert not result.approved
    open_order.status = open_order.status.CANCELLED
    assert RiskManager(LIMITS).validate("AAPL", Side.BUY, Decimal("50"), Decimal("50"), Decimal("0"), [open_order]).approved


def test_sell_order_projects_negative_position() -> None:
    result = RiskManager(LIMITS).validate("AAPL", Side.SELL, Decimal("80"), Decimal("100"), Decimal("20"), [])
    assert result.projected_position == Decimal("-60")


def test_symbol_specific_limits_override_default() -> None:
    manager = RiskManager(LIMITS, {"AAPL": RiskLimits(Decimal("10"), Decimal("1000"))})
    assert not manager.validate("AAPL", Side.BUY, Decimal("11"), Decimal("1"), Decimal("0"), []).approved
    assert manager.validate("MSFT", Side.BUY, Decimal("11"), Decimal("1"), Decimal("0"), []).approved
