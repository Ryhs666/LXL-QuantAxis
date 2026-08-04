from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.lxl_quantaxis.execution.orders import MarketQuote, Order, OrderSide, OrderStatus
from src.lxl_quantaxis.execution.paper_trading import PaperBroker

NOW = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def _order(order_id: str, side: OrderSide, quantity: int = 200) -> Order:
    return Order(order_id, "600000", side, quantity, NOW)


class PaperBrokerTests(unittest.TestCase):
    def test_submission_is_idempotent_and_rejects_key_reuse(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("10000"))
        accepted = broker.submit(_order("o-1", OrderSide.BUY))
        self.assertIs(broker.submit(_order("o-1", OrderSide.BUY)), accepted)
        with self.assertRaisesRegex(ValueError, "idempotency"):
            broker.submit(_order("o-1", OrderSide.BUY, 300))

    def test_board_lot_and_limit_rules(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("10000"))
        rejected = broker.submit(_order("odd", OrderSide.BUY, 150))
        self.assertIs(rejected.status, OrderStatus.REJECTED)
        broker.submit(_order("limit", OrderSide.BUY))
        fill = broker.execute("limit", MarketQuote("600000", Decimal("10"), 200, limit_up=True), executed_at=NOW)
        self.assertIsNone(fill)

    def test_partial_fill_then_complete_and_reconcile(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("10000"))
        broker.submit(_order("o-1", OrderSide.BUY, 300))
        first = broker.execute("o-1", MarketQuote("600000", Decimal("10"), 100), executed_at=NOW)
        self.assertEqual(first.quantity if first else None, 100)
        self.assertIs(broker.orders["o-1"].status, OrderStatus.PARTIALLY_FILLED)
        broker.execute("o-1", MarketQuote("600000", Decimal("10"), 200), executed_at=NOW)
        self.assertIs(broker.orders["o-1"].status, OrderStatus.FILLED)
        self.assertTrue(broker.reconcile().balanced)

    def test_t_plus_one_blocks_same_day_sell(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("10000"))
        broker.submit(_order("buy", OrderSide.BUY))
        broker.execute("buy", MarketQuote("600000", Decimal("10"), 200), executed_at=NOW)
        broker.submit(_order("sell", OrderSide.SELL))
        self.assertIsNone(broker.execute("sell", MarketQuote("600000", Decimal("10"), 200), executed_at=NOW))
        fill = broker.execute(
            "sell",
            MarketQuote("600000", Decimal("11"), 200),
            executed_at=NOW + timedelta(days=1),
        )
        self.assertEqual(fill.quantity if fill else None, 200)
        self.assertTrue(broker.reconcile().balanced)

    def test_limit_down_blocks_sell(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("10000"))
        broker.submit(_order("buy", OrderSide.BUY))
        broker.execute("buy", MarketQuote("600000", Decimal("10"), 200), executed_at=NOW)
        broker.submit(_order("sell", OrderSide.SELL))
        self.assertIsNone(
            broker.execute(
                "sell",
                MarketQuote("600000", Decimal("9"), 200, limit_down=True),
                executed_at=NOW + timedelta(days=1),
            )
        )


if __name__ == "__main__":
    unittest.main()
