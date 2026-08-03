"""Behavior tests for financial and temporal value objects."""

import unittest
from datetime import datetime
from decimal import Decimal

from src.lxl_quantaxis.core.contracts import Instant, Instrument, Market, Money, TimeRange


class InstrumentTests(unittest.TestCase):
    def test_instrument_normalizes_supported_markets(self) -> None:
        self.assertEqual(str(Instrument.create("600519", Market.CN)), "CN:600519")
        self.assertEqual(str(Instrument.create("700", Market.HK)), "HK:00700")
        self.assertEqual(str(Instrument.create("aapl", Market.US)), "US:AAPL")
        self.assertEqual(Instrument.parse("INDEX:000300"), Instrument.create("000300", Market.INDEX))

    def test_instrument_rejects_invalid_symbol(self) -> None:
        with self.assertRaises(ValueError):
            Instrument.create("60051", Market.CN)
        with self.assertRaises(ValueError):
            Instrument.parse("UNKNOWN:ABC")


class MoneyTests(unittest.TestCase):
    def test_money_uses_decimal_and_serializes_exactly(self) -> None:
        money = Money.of("12.340", "cny")

        self.assertEqual(money.amount, Decimal("12.340"))
        self.assertEqual(money.currency, "CNY")
        self.assertEqual(Money.from_dict(money.to_dict()), money)
        self.assertEqual(money + Money.of("0.660", "CNY"), Money.of("13.000", "CNY"))

    def test_money_rejects_float_and_currency_mismatch(self) -> None:
        with self.assertRaises(TypeError):
            Money.of(0.1, "CNY")
        with self.assertRaises(ValueError):
            _ = Money.of("1", "CNY") + Money.of("1", "USD")


class TimeContractTests(unittest.TestCase):
    def test_instant_normalizes_to_utc_and_round_trips(self) -> None:
        instant = Instant.parse("2026-08-03T12:00:00+08:00")

        self.assertEqual(instant.isoformat(), "2026-08-03T04:00:00Z")
        self.assertEqual(Instant.parse(instant.isoformat()), instant)

    def test_naive_time_and_reverse_range_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Instant(datetime(2026, 8, 3, 12, 0))

        start = Instant.parse("2026-08-03T04:00:00Z")
        end = Instant.parse("2026-08-03T03:59:59Z")
        with self.assertRaises(ValueError):
            TimeRange(start=start, end=end)


if __name__ == "__main__":
    unittest.main()
