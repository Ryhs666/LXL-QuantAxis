"""Golden tests for signal availability and deterministic next-bar fills."""

from __future__ import annotations

import unittest

from src.backtest.engine import BacktestEngine
from tests.fixtures.legacy_backtest import BuyOnSecondBar, without_audit_files
from tests.fixtures.market_bars import daily_bars


def _engine(**overrides: object) -> BacktestEngine:
    settings: dict[str, object] = {
        "commission_rate": 0.0,
        "slippage": 0.0,
        "use_risk_manager": False,
        "use_impact_cost": False,
        "use_limit_order": False,
        "random_seed": 17,
    }
    settings.update(overrides)
    return BacktestEngine(**settings)


class NextBarExecutionTests(unittest.TestCase):
    def test_close_signal_fills_at_next_open(self) -> None:
        bars = daily_bars()
        with without_audit_files():
            result = _engine().run(BuyOnSecondBar(), bars)

        buy = result["portfolio"].trade_log[0]
        self.assertEqual(buy["date"], str(bars.iloc[2]["date"])[:10])
        self.assertEqual(buy["price"], float(bars.iloc[2]["open"]))
        self.assertEqual(result["execution_semantics"], "next_bar_open")
        self.assertGreater(
            result["signals"][0]["earliest_execution_at"],
            result["signals"][0]["available_at"],
        )

    def test_future_close_change_does_not_change_signal_or_fill_price(self) -> None:
        original = daily_bars()
        changed = original.copy()
        changed.loc[2, "close"] = 10_000.0
        with without_audit_files():
            first = _engine().run(BuyOnSecondBar(), original)
            second = _engine().run(BuyOnSecondBar(), changed)

        self.assertEqual(first["signals"], second["signals"])
        self.assertEqual(first["portfolio"].trade_log, second["portfolio"].trade_log)

    def test_fixed_seed_reproduces_stochastic_fill_sequence(self) -> None:
        bars = daily_bars()
        with without_audit_files():
            first = _engine(use_limit_order=True).run(BuyOnSecondBar(), bars)
            second = _engine(use_limit_order=True).run(BuyOnSecondBar(), bars)

        self.assertEqual(first["portfolio"].trade_log, second["portfolio"].trade_log)
        self.assertEqual(first["metrics"], second["metrics"])

    def test_legacy_mode_is_explicit_and_produces_old_same_bar_fill(self) -> None:
        bars = daily_bars()
        with without_audit_files():
            modern = _engine().run(BuyOnSecondBar(), bars)
            legacy = _engine(legacy_backtest_mode=True).run(BuyOnSecondBar(), bars)

        self.assertEqual(modern["portfolio"].trade_log[0]["price"], float(bars.iloc[2]["open"]))
        self.assertEqual(legacy["portfolio"].trade_log[0]["price"], float(bars.iloc[1]["close"]))


if __name__ == "__main__":
    unittest.main()
