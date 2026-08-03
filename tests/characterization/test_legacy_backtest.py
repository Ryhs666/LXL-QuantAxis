"""Characterize known correctness gaps in the legacy backtest contract."""

from __future__ import annotations

import unittest

from src.backtest.engine import BacktestEngine
from src.backtest.metrics import calc_all_metrics
from tests.fixtures.legacy_backtest import BuyOnSecondBar, without_audit_files
from tests.fixtures.market_bars import daily_bars


class TestLegacyBacktestTiming(unittest.TestCase):
    @unittest.expectedFailure
    def test_fill_occurs_after_signal_data_is_available(self):
        """Known C-01: close(t) signal currently fills at close(t)."""
        bars = daily_bars()
        engine = BacktestEngine(
            commission_rate=0.0,
            slippage=0.0,
            use_risk_manager=False,
            use_impact_cost=False,
            use_limit_order=False,
        )

        with without_audit_files():
            result = engine.run(BuyOnSecondBar(), bars)

        buy = next(
            trade
            for trade in result["portfolio"].trade_log
            if trade["action"] == "BUY"
        )
        signal_date = str(bars.iloc[1]["date"])[:10]

        self.assertGreater(
            buy["date"],
            signal_date,
            "a close-derived signal must execute after its availability time",
        )


class TestLegacyMetricTypes(unittest.TestCase):
    @unittest.expectedFailure
    def test_domain_metrics_are_numeric(self):
        """Known M-07: domain metrics currently contain display strings."""
        metrics = calc_all_metrics(
            daily_values=[
                {"date": "2024-01-02", "total_value": 100_000.0},
                {"date": "2024-01-03", "total_value": 101_000.0},
            ],
            trade_log=[],
            initial_capital=100_000.0,
        )

        for name in ("总收益率", "年化收益率", "最大回撤", "胜率", "盈利因子"):
            with self.subTest(metric=name):
                self.assertIsInstance(metrics[name], (int, float))


if __name__ == "__main__":
    unittest.main()
