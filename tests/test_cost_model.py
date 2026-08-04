"""Tests for centralized transaction cost model."""

import pytest
from src.lxl_quantaxis.backtest.cost_model import (
    CostConfig,
    CostBreakdown,
    OrderSide,
    calculate_cost,
    is_shanghai,
    A_SHARE_COST,
)


class TestIsShanghai:
    def test_60xxxx(self):
        assert is_shanghai("600519")

    def test_00xxxx_is_shenzhen(self):
        assert not is_shanghai("000001")

    def test_30xxxx_is_shenzhen(self):
        assert not is_shanghai("300750")

    def test_688xxx_is_shanghai(self):
        assert is_shanghai("688001")

    def test_empty_returns_false(self):
        assert not is_shanghai("")


class TestCalculateCost:
    def test_buy_commission(self):
        c = calculate_cost(100.0, 100, OrderSide.BUY, is_shanghai=False)
        assert c.commission == 5.0  # min commission
        assert c.stamp_duty == 0.0  # no stamp duty on buy
        assert c.transfer_fee == 0.0

    def test_sell_stamp_duty(self):
        c = calculate_cost(100.0, 100, OrderSide.SELL)
        assert c.stamp_duty == pytest.approx(5.0)  # 0.05% of 10,000

    def test_shanghai_transfer_fee(self):
        c = calculate_cost(100.0, 100, OrderSide.BUY, is_shanghai=True)
        # transfer fee: 0.00001 * 10000 = 0.1
        assert c.transfer_fee == pytest.approx(0.1)

    def test_cover_no_stamp_duty(self):
        """Closing a short should NOT be charged stamp duty."""
        c = calculate_cost(100.0, 100, OrderSide.COVER)
        assert c.stamp_duty == 0.0

    def test_buy_net_higher_than_gross(self):
        """Buy: you pay more than the gross amount."""
        c = calculate_cost(100.0, 100, OrderSide.BUY, is_shanghai=True)
        assert c.net_amount > c.gross_amount

    def test_sell_net_lower_than_gross(self):
        """Sell: you receive less than the gross amount."""
        c = calculate_cost(100.0, 100, OrderSide.SELL, is_shanghai=True)
        assert c.net_amount < c.gross_amount

    def test_non_negative_total_fee(self):
        c = calculate_cost(1.0, 1, OrderSide.BUY)
        assert c.total_fee > 0

    def test_large_order_commission(self):
        """Large order: commission > min."""
        c = calculate_cost(100.0, 100000, OrderSide.BUY)  # 10M order
        expected = 10000000 * 0.0003  # 3000
        assert c.commission == pytest.approx(expected)

    def test_zero_price_raises(self):
        with pytest.raises(ValueError):
            calculate_cost(0, 100, OrderSide.BUY)

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError):
            calculate_cost(100, 0, OrderSide.BUY)


class TestCostConfig:
    def test_default_no_short(self):
        assert not A_SHARE_COST.short_enabled

    def test_negative_commission_raises(self):
        with pytest.raises(ValueError):
            CostConfig(commission_rate=-0.01)

    def test_transfer_fee_rate_is_correct(self):
        """The transfer fee rate 0.00001 = 0.001% per official A-share schedule."""
        assert A_SHARE_COST.transfer_fee_rate == 0.00001
