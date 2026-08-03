"""Accounting identities, FIFO lots, corporate actions, and typed metrics."""

from __future__ import annotations

import math
import unittest
from datetime import UTC, datetime
from decimal import Decimal

from src.backtest.engine import Portfolio
from src.backtest.metrics import calc_all_metrics, format_metrics_for_display
from src.lxl_quantaxis.backtest.performance import calculate_performance
from src.lxl_quantaxis.portfolio import CashDividend, FillSide, PortfolioLedger, TradeFill

D = Decimal
NOW = datetime(2026, 8, 3, tzinfo=UTC)


def _fill(fill_id: str, side: FillSide, quantity: int, price: str, **values: object) -> TradeFill:
    return TradeFill(
        fill_id=fill_id,
        executed_at=NOW,
        symbol=str(values.get("symbol", "600000")),
        side=side,
        quantity=quantity,
        price=D(price),
        fee=D(str(values.get("fee", "0"))),
        tax=D(str(values.get("tax", "0"))),
        currency=str(values.get("currency", "CNY")),
    )


class ImmutableLedgerTests(unittest.TestCase):
    def test_fifo_partial_sale_and_accounting_identity(self) -> None:
        empty = PortfolioLedger(D("10000"))
        ledger = empty.post_fill(_fill("b1", FillSide.BUY, 100, "10"))
        ledger = ledger.post_fill(_fill("b2", FillSide.BUY, 100, "20"))
        ledger = ledger.post_fill(_fill("s1", FillSide.SELL, 150, "30", fee="5"))

        state = ledger.state()
        valuation = ledger.value({"600000": D("25")})
        self.assertEqual(empty.entries, ())
        self.assertEqual(state.positions["600000"].quantity, 50)
        self.assertEqual(state.positions["600000"].average_cost, D("20"))
        self.assertEqual(state.realized_pnl["CNY"], D("2495"))
        self.assertEqual(valuation.total, valuation.cash + valuation.positions)
        self.assertEqual(valuation.total, D("12745"))

    def test_dividend_and_multi_currency_valuation(self) -> None:
        ledger = PortfolioLedger(D("10000"))
        ledger = ledger.post_fill(_fill("usd-buy", FillSide.BUY, 10, "10", symbol="AAPL", currency="USD"))
        ledger = ledger.post_dividend(CashDividend("div-1", NOW, "AAPL", D("5"), "USD"))

        valuation = ledger.value({"AAPL": D("12")}, {"USD": D("7")})
        self.assertEqual(ledger.state().dividends["USD"], D("5"))
        self.assertEqual(valuation.total, D("10175"))

    def test_oversell_and_duplicate_fill_are_rejected(self) -> None:
        buy = _fill("b1", FillSide.BUY, 10, "10")
        ledger = PortfolioLedger(D("1000")).post_fill(buy)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ledger.post_fill(buy)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            ledger.post_fill(_fill("s1", FillSide.SELL, 11, "12"))

    def test_accounting_identity_holds_across_position_sizes(self) -> None:
        for quantity in (1, 10, 100, 1000):
            with self.subTest(quantity=quantity):
                ledger = PortfolioLedger(D("100000")).post_fill(_fill(f"b-{quantity}", FillSide.BUY, quantity, "8"))
                value = ledger.value({"600000": D("9")})
                self.assertEqual(value.total, value.cash + value.positions)

    def test_legacy_portfolio_can_be_replayed(self) -> None:
        portfolio = Portfolio(10_000)
        portfolio.buy("600000", 10.0, 100, "2026-08-01", commission_rate=0.0)
        portfolio.sell("600000", 12.0, 40, "2026-08-02", commission_rate=0.0)

        state = portfolio.to_immutable_ledger().state()
        self.assertEqual(state.positions["600000"].quantity, 60)
        self.assertEqual(state.realized_pnl["CNY"], D("80.0"))


class TypedPerformanceTests(unittest.TestCase):
    def test_metrics_are_numeric_and_display_formatting_is_separate(self) -> None:
        daily = [
            {"date": "d1", "total_value": 100.0},
            {"date": "d2", "total_value": 120.0},
            {"date": "d3", "total_value": 90.0},
            {"date": "d4", "total_value": 110.0},
        ]
        trades = [{"action": "SELL", "pnl": 20.0}, {"action": "SELL", "pnl": -10.0}]

        typed = calculate_performance(daily, trades, 100.0)
        legacy = calc_all_metrics(daily, trades, 100.0)
        display = format_metrics_for_display(legacy)

        self.assertAlmostEqual(typed.total_return, 0.1)
        self.assertAlmostEqual(typed.max_drawdown, -0.25)
        self.assertEqual(typed.profit_factor, 2.0)
        self.assertIsInstance(legacy["总收益率"], float)
        self.assertEqual(display["总收益率"], "+10.00%")
        self.assertFalse(math.isnan(typed.sharpe_ratio))


if __name__ == "__main__":
    unittest.main()
