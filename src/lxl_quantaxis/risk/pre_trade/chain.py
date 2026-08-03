"""Fail-closed, versioned pre-trade risk evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OrderIntent:
    order_id: str
    action: str
    symbol: str
    quantity: int
    price: float
    sector: str = "unknown"
    average_daily_volume: float | None = None
    volatility: float | None = None

    @property
    def notional(self) -> float:
        return self.quantity * self.price

    @property
    def opens_risk(self) -> bool:
        return self.action in {"BUY", "SHORT"}


@dataclass(frozen=True, slots=True)
class PortfolioRiskSnapshot:
    equity: float
    cash: float
    peak_equity: float
    position_values: Mapping[str, float]
    sector_values: Mapping[str, float]
    kill_switch: bool = False


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    policy_id: str
    policy_version: str
    reason: str


@dataclass(frozen=True, slots=True)
class ChainDecision:
    approved: bool
    decisions: tuple[RiskDecision, ...]

    @property
    def reason(self) -> str:
        rejected = next((item.reason for item in self.decisions if not item.approved), "")
        return rejected


class RiskPolicy(Protocol):
    policy_id: str
    version: str

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> RiskDecision: ...


@dataclass(frozen=True, slots=True)
class RiskPolicyChain:
    policies: tuple[RiskPolicy, ...]

    def evaluate(self, order: OrderIntent, portfolio: PortfolioRiskSnapshot) -> ChainDecision:
        decisions: list[RiskDecision] = []
        for policy in self.policies:
            try:
                decision = policy.evaluate(order, portfolio)
            except Exception as exc:
                decision = RiskDecision(False, policy.policy_id, policy.version, f"policy error: {type(exc).__name__}")
            decisions.append(decision)
            if not decision.approved:
                return ChainDecision(False, tuple(decisions))
        return ChainDecision(True, tuple(decisions))
