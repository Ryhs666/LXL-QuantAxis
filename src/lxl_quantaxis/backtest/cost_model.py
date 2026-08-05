"""Centralized, testable transaction cost model.

All cost calculations flow through this single module.
No fee formulas duplicated across engine/portfolio/broker.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"     # open short — experimental, default disabled
    COVER = "COVER"     # close short — experimental


@dataclass(frozen=True, slots=True)
class CostConfig:
    """Trading cost parameters for a single market."""

    commission_rate: float = 0.0003      # 0.03% per trade
    min_commission: float = 5.0          # minimum per trade (CNY)
    stamp_duty_rate: float = 0.0005      # 0.05% (sell only in A-shares)
    transfer_fee_rate: float = 0.00001   # 0.001% (SH market only, both sides)

    # Must be set explicitly; there is no silent default.
    short_enabled: bool = False
    short_borrow_rate_annual: float = 0.02  # annual borrow cost
    short_margin_requirement: float = 1.30  # 130% of short value


    def __post_init__(self) -> None:
        if self.commission_rate < 0:
            raise ValueError("commission_rate must be non-negative")
        if self.min_commission < 0:
            raise ValueError("min_commission must be non-negative")
        if self.stamp_duty_rate < 0:
            raise ValueError("stamp_duty_rate must be non-negative")
        # Note: transfer_fee_rate of 0.00001 = 0.001% (1 per 100,000)
        # This is per the official A-share fee schedule.


# Default A-share cost config
A_SHARE_COST = CostConfig()


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Immutable cost breakdown for a single trade."""
    gross_amount: float     # price * quantity
    commission: float       # brokerage commission
    stamp_duty: float       # stamp duty (sell only)
    transfer_fee: float     # SH transfer fee
    total_fee: float        # commission + stamp_duty + transfer_fee
    net_amount: float       # gross_amount ± total_fee (+ for buy, - for sell)


def calculate_cost(
    price: float,
    quantity: int,
    side: OrderSide,
    is_shanghai: bool = False,
    config: CostConfig = A_SHARE_COST,
) -> CostBreakdown:
    """Calculate transaction cost for a single order.

    Args:
        price: execution price per share
        quantity: number of shares
        side: BUY / SELL / SHORT / COVER
        is_shanghai: True if the stock is listed on Shanghai exchange
        config: cost parameters

    Returns:
        CostBreakdown with all fee components
    """
    if price <= 0 or quantity <= 0:
        raise ValueError(f"price={price}, quantity={quantity} must be positive")

    gross = price * quantity

    # Commission (minimum applies)
    commission = max(gross * config.commission_rate, config.min_commission)

    # Stamp duty: SELL side only (A-shares).  SHORT/COVER are experimental.
    stamp_duty = 0.0
    if side == OrderSide.SELL:
        stamp_duty = gross * config.stamp_duty_rate
    # COVER (closing a short) is NOT a regular sell — no stamp duty
    if side == OrderSide.COVER:
        stamp_duty = 0.0

    # Transfer fee: SH market only, both buy and sell
    transfer_fee = gross * config.transfer_fee_rate if is_shanghai else 0.0

    total_fee = commission + stamp_duty + transfer_fee

    if side in (OrderSide.BUY, OrderSide.COVER):
        net = gross + total_fee  # you pay
    else:
        net = gross - total_fee  # you receive

    return CostBreakdown(
        gross_amount=round(gross, 2),
        commission=round(commission, 2),
        stamp_duty=round(stamp_duty, 2),
        transfer_fee=round(transfer_fee, 2),
        total_fee=round(total_fee, 2),
        net_amount=round(net, 2),
    )


def is_shanghai(symbol: str) -> bool:
    """Determine if a symbol is listed on Shanghai exchange."""
    s = str(symbol).strip().upper()
    return s.startswith("6") or s.startswith("588") or s.startswith("51")
