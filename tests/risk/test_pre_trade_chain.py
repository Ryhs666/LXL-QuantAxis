"""Boundary, composition, rejection, and audit tests for pre-trade risk."""

from __future__ import annotations

import unittest

from src.backtest.engine import BacktestEngine
from src.lxl_quantaxis.risk.policies import (
    CashPolicy,
    DrawdownPolicy,
    KillSwitchPolicy,
    PositionLimitPolicy,
)
from src.lxl_quantaxis.risk.pre_trade import OrderIntent, PortfolioRiskSnapshot, RiskPolicyChain
from tests.fixtures.legacy_backtest import BuyOnSecondBar, without_audit_files
from tests.fixtures.market_bars import daily_bars


def _order(**values: object) -> OrderIntent:
    defaults: dict[str, object] = {
        "order_id": "o-1",
        "action": "BUY",
        "symbol": "600000",
        "quantity": 100,
        "price": 10.0,
    }
    defaults.update(values)
    return OrderIntent(**defaults)


def _snapshot(**values: object) -> PortfolioRiskSnapshot:
    defaults: dict[str, object] = {
        "equity": 10_000.0,
        "cash": 10_000.0,
        "peak_equity": 10_000.0,
        "position_values": {},
        "sector_values": {},
    }
    defaults.update(values)
    return PortfolioRiskSnapshot(**defaults)


class PreTradePolicyTests(unittest.TestCase):
    def test_position_limit_accepts_boundary_and_rejects_excess(self) -> None:
        policy = PositionLimitPolicy(maximum=0.1)
        self.assertTrue(policy.evaluate(_order(), _snapshot()).approved)
        self.assertFalse(policy.evaluate(_order(quantity=101), _snapshot()).approved)

    def test_chain_stops_at_first_rejection_and_preserves_version(self) -> None:
        chain = RiskPolicyChain((KillSwitchPolicy(), CashPolicy(), DrawdownPolicy(maximum=0.1)))
        decision = chain.evaluate(_order(), _snapshot(cash=0.0))

        self.assertFalse(decision.approved)
        self.assertEqual(len(decision.decisions), 2)
        self.assertEqual(decision.decisions[-1].policy_id, "risk.cash")
        self.assertEqual(decision.decisions[-1].policy_version, "1.0.0")

    def test_rejected_order_never_reaches_portfolio(self) -> None:
        chain = RiskPolicyChain((KillSwitchPolicy(),))
        bars = daily_bars()
        engine = BacktestEngine(
            commission_rate=0.0,
            slippage=0.0,
            use_risk_manager=False,
            use_impact_cost=False,
            risk_policy_chain=chain,
        )
        with without_audit_files():
            result = engine.run(BuyOnSecondBar(), bars)
        self.assertEqual(len(result["portfolio"].trade_log), 1)

        blocked = BacktestEngine(
            commission_rate=0.0,
            slippage=0.0,
            use_risk_manager=False,
            use_impact_cost=False,
            risk_policy_chain=RiskPolicyChain((PositionLimitPolicy(maximum=0.001),)),
        )
        with without_audit_files():
            rejected = blocked.run(BuyOnSecondBar(), bars)
        self.assertEqual(rejected["portfolio"].trade_log, [])
        self.assertEqual(rejected["risk_decisions"][0].decisions[-1].policy_id, "risk.position-limit")


if __name__ == "__main__":
    unittest.main()
