"""Composable pre-trade risk limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.lxl_quantaxis.risk.pre_trade import OrderIntent, PortfolioRiskSnapshot, RiskDecision


class _Policy:
    policy_id = "risk.base"
    version = "1.0.0"

    def decision(self, approved: bool, reason: str = "approved") -> RiskDecision:
        return RiskDecision(approved, self.policy_id, self.version, reason)


class KillSwitchPolicy(_Policy):
    policy_id = "risk.kill-switch"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        return self.decision(
            not portfolio.kill_switch, "kill switch is active" if portfolio.kill_switch else "approved"
        )


@dataclass(frozen=True, slots=True)
class DrawdownPolicy(_Policy):
    maximum: float = 0.1
    policy_id = "risk.drawdown"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        drawdown = 1.0 - portfolio.equity / portfolio.peak_equity if portfolio.peak_equity > 0 else 1.0
        approved = not order.opens_risk or drawdown < self.maximum
        return self.decision(approved, "maximum drawdown reached" if not approved else "approved")


@dataclass(frozen=True, slots=True)
class PositionLimitPolicy(_Policy):
    maximum: float = 0.15
    policy_id = "risk.position-limit"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        current = portfolio.position_values.get(order.symbol, 0.0)
        ratio = (current + order.notional) / portfolio.equity if portfolio.equity > 0 else 1.0
        approved = not order.opens_risk or ratio <= self.maximum
        return self.decision(approved, "single-position limit exceeded" if not approved else "approved")


class CashPolicy(_Policy):
    policy_id = "risk.cash"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        approved = order.action != "BUY" or order.notional <= portfolio.cash
        return self.decision(approved, "insufficient cash" if not approved else "approved")


@dataclass(frozen=True, slots=True)
class LiquidityPolicy(_Policy):
    maximum_participation: float = 0.05
    policy_id = "risk.liquidity"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        del portfolio
        approved = (
            order.average_daily_volume is None
            or order.quantity <= order.average_daily_volume * self.maximum_participation
        )
        return self.decision(approved, "liquidity participation limit exceeded" if not approved else "approved")


@dataclass(frozen=True, slots=True)
class SectorLimitPolicy(_Policy):
    maximum: float = 0.3
    policy_id = "risk.sector-limit"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        projected = portfolio.sector_values.get(order.sector, 0.0) + order.notional
        approved = not order.opens_risk or (portfolio.equity > 0 and projected / portfolio.equity <= self.maximum)
        return self.decision(approved, "sector exposure limit exceeded" if not approved else "approved")


@dataclass(frozen=True, slots=True)
class VolatilityPolicy(_Policy):
    maximum: float = 0.6
    policy_id = "risk.volatility"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        del portfolio
        approved = order.volatility is None or order.volatility <= self.maximum
        return self.decision(approved, "volatility limit exceeded" if not approved else "approved")


@dataclass(frozen=True, slots=True)
class LegacyRiskPolicy(_Policy):
    manager: Any
    policy_id = "risk.legacy-adapter"

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision:
        del portfolio
        if not order.opens_risk:
            return self.decision(True)
        approved, reason = self.manager.can_open_new()
        return self.decision(bool(approved), str(reason) if not approved else "approved")
