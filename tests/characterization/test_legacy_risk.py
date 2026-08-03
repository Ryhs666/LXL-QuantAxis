"""Characterize the legacy ordering between risk checks and execution."""

from __future__ import annotations

import unittest

from src.backtest.engine import BacktestEngine
from tests.fixtures.legacy_backtest import BuyOnSecondBar, without_audit_files
from tests.fixtures.market_bars import daily_bars


class _TriggeredCircuitBreaker:
    circuit_triggered = True
    circuit_reason = "characterization circuit already active"

    def update_equity(self, equity):
        return None

    def report(self):
        return "circuit active"

    def get_recent_logs(self, count):
        return []


class TestLegacyRiskOrdering(unittest.TestCase):
    def test_active_circuit_breaker_rejects_buy_before_fill(self):
        """C-02 regression: an active circuit breaker rejects before execution."""
        engine = BacktestEngine(
            commission_rate=0.0,
            slippage=0.0,
            use_risk_manager=False,
            use_impact_cost=False,
            use_limit_order=False,
        )
        engine.risk = _TriggeredCircuitBreaker()

        with without_audit_files():
            result = engine.run(BuyOnSecondBar(), daily_bars())

        buys = [
            trade
            for trade in result["portfolio"].trade_log
            if trade["action"] == "BUY"
        ]
        self.assertEqual(
            buys,
            [],
            "an active circuit breaker must reject BUY before execution",
        )


if __name__ == "__main__":
    unittest.main()
