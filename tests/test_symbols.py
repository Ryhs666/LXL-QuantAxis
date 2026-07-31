"""Tests for market and symbol normalization."""
import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.symbols import (
    normalize_market,
    normalize_symbol,
    instrument_key,
)
from src.backtest import data_feed


# ============================================================
# normalize_market
# ============================================================

class TestNormalizeMarket(unittest.TestCase):
    """Test market name normalization for all aliases."""

    # ---- A股 ----
    def test_a_share_aliases(self):
        for alias in ["A股", "A", "CN", "CHINA"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "A股")

    def test_a_share_case_insensitive(self):
        for alias in ["a", "cn", "china", "China", "cN"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "A股")

    # ---- 美股 ----
    def test_us_aliases(self):
        for alias in ["美股", "US", "USA"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "美股")

    def test_us_case_insensitive(self):
        for alias in ["us", "usa", "Us", "Usa"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "美股")

    # ---- 港股 ----
    def test_hk_aliases(self):
        for alias in ["港股", "HK", "HONGKONG"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "港股")

    def test_hk_case_insensitive(self):
        for alias in ["hk", "hongkong", "Hk", "HongKong"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "港股")

    # ---- 指数 ----
    def test_index_aliases(self):
        for alias in ["指数", "INDEX", "IDX"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "指数")

    def test_index_case_insensitive(self):
        for alias in ["index", "idx", "Index", "Idx"]:
            with self.subTest(alias=alias):
                self.assertEqual(normalize_market(alias), "指数")

    # ---- 空格 ----
    def test_whitespace_stripped(self):
        self.assertEqual(normalize_market("  A股  "), "A股")
        self.assertEqual(normalize_market("\tcn\n"), "A股")
        self.assertEqual(normalize_market("  us  "), "美股")

    # ---- 非法输入 ----
    def test_none_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_market(None)

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_market("")

    def test_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_market("   ")

    def test_unknown_market_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_market("火星")
        with self.assertRaises(ValueError):
            normalize_market("JP")


# ============================================================
# normalize_symbol
# ============================================================

class TestNormalizeSymbol(unittest.TestCase):
    """Test symbol code normalization for all four markets."""

    # ---- A股 ----
    def test_a_stock_pure_digits(self):
        self.assertEqual(normalize_symbol("600519", "A股"), "600519")
        self.assertEqual(normalize_symbol("000001", "A股"), "000001")

    def test_a_stock_sh_prefix(self):
        self.assertEqual(normalize_symbol("sh600519", "A股"), "600519")
        self.assertEqual(normalize_symbol("SH600519", "A股"), "600519")

    def test_a_stock_sh_dot_prefix(self):
        self.assertEqual(normalize_symbol("SH.600519", "A股"), "600519")
        self.assertEqual(normalize_symbol("sh.600519", "A股"), "600519")

    def test_a_stock_sz_prefix(self):
        self.assertEqual(normalize_symbol("sz000001", "A股"), "000001")
        self.assertEqual(normalize_symbol("SZ000001", "A股"), "000001")
        self.assertEqual(normalize_symbol("SZ.000001", "A股"), "000001")

    def test_a_stock_does_not_auto_pad(self):
        """A股不自动补齐 — 5位数字应该报错。"""
        with self.assertRaises(ValueError):
            normalize_symbol("60519", "A股")

    def test_a_stock_invalid_too_long(self):
        with self.assertRaises(ValueError):
            normalize_symbol("6005190", "A股")

    def test_a_stock_invalid_letters(self):
        with self.assertRaises(ValueError):
            normalize_symbol("abcdef", "A股")

    def test_a_stock_invalid_mixed(self):
        with self.assertRaises(ValueError):
            normalize_symbol("60051a", "A股")

    # ---- 指数 ----
    def test_index_pure_digits(self):
        self.assertEqual(normalize_symbol("000300", "指数"), "000300")
        self.assertEqual(normalize_symbol("399006", "指数"), "399006")

    def test_index_sh_prefix(self):
        self.assertEqual(normalize_symbol("sh000300", "指数"), "000300")
        self.assertEqual(normalize_symbol("SH.000300", "指数"), "000300")

    def test_index_invalid_short(self):
        with self.assertRaises(ValueError):
            normalize_symbol("00300", "指数")

    # ---- 港股 ----
    def test_hk_stock_pad_to_5(self):
        self.assertEqual(normalize_symbol("700", "港股"), "00700")
        self.assertEqual(normalize_symbol("0700", "港股"), "00700")
        self.assertEqual(normalize_symbol("00700", "港股"), "00700")
        self.assertEqual(normalize_symbol("1", "港股"), "00001")
        self.assertEqual(normalize_symbol("12345", "港股"), "12345")

    def test_hk_stock_dot_hk_suffix(self):
        self.assertEqual(normalize_symbol("0700.HK", "港股"), "00700")
        self.assertEqual(normalize_symbol("700.HK", "港股"), "00700")
        self.assertEqual(normalize_symbol("00700.HK", "港股"), "00700")
        self.assertEqual(normalize_symbol("0700.hk", "港股"), "00700")

    def test_hk_stock_invalid_letters(self):
        with self.assertRaises(ValueError):
            normalize_symbol("abc", "港股")

    def test_hk_stock_invalid_too_long(self):
        with self.assertRaises(ValueError):
            normalize_symbol("123456", "港股")

    # ---- 美股 ----
    def test_us_stock_uppercase(self):
        self.assertEqual(normalize_symbol("aapl", "美股"), "AAPL")
        self.assertEqual(normalize_symbol("AAPL", "美股"), "AAPL")
        self.assertEqual(normalize_symbol("Aapl", "美股"), "AAPL")

    def test_us_stock_exchange_prefix(self):
        self.assertEqual(normalize_symbol("nasdaq:aapl", "美股"), "AAPL")
        self.assertEqual(normalize_symbol("NASDAQ:AAPL", "美股"), "AAPL")
        self.assertEqual(normalize_symbol("nyse:brk.b", "美股"), "BRK.B")
        self.assertEqual(normalize_symbol("NYSE:GE", "美股"), "GE")

    def test_us_stock_dot_dash_preserved(self):
        self.assertEqual(normalize_symbol("BRK.B", "美股"), "BRK.B")
        self.assertEqual(normalize_symbol("BRK-B", "美股"), "BRK-B")
        self.assertEqual(normalize_symbol("brk.b", "美股"), "BRK.B")

    def test_us_stock_invalid_digits(self):
        with self.assertRaises(ValueError):
            normalize_symbol("12345", "美股")

    def test_us_stock_invalid_too_long(self):
        with self.assertRaises(ValueError):
            normalize_symbol("TOOLONG", "美股")

    # ---- 通用非法输入 ----
    def test_none_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_symbol(None, "A股")

    def test_empty_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_symbol("", "A股")

    def test_whitespace_only_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_symbol("   ", "A股")

    def test_invalid_market_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_symbol("600519", "火星")

    def test_market_alias_normalized_in_symbol(self):
        """normalize_symbol 也会标准化 market 参数。"""
        self.assertEqual(normalize_symbol("AAPL", "us"), "AAPL")
        self.assertEqual(normalize_symbol("0700.hk", "hongkong"), "00700")


# ============================================================
# instrument_key
# ============================================================

class TestInstrumentKey(unittest.TestCase):
    """Test instrument_key generation."""

    def test_cn_key(self):
        self.assertEqual(instrument_key("600519", "A股"), "CN:600519")
        self.assertEqual(instrument_key("sh600519", "A股"), "CN:600519")
        self.assertEqual(instrument_key("000001", "CN"), "CN:000001")

    def test_us_key(self):
        self.assertEqual(instrument_key("AAPL", "美股"), "US:AAPL")
        self.assertEqual(instrument_key("aapl", "us"), "US:AAPL")
        self.assertEqual(instrument_key("nyse:brk.b", "USA"), "US:BRK.B")

    def test_hk_key(self):
        self.assertEqual(instrument_key("00700", "港股"), "HK:00700")
        self.assertEqual(instrument_key("700", "hk"), "HK:00700")
        self.assertEqual(instrument_key("0700.HK", "HONGKONG"), "HK:00700")

    def test_index_key(self):
        self.assertEqual(instrument_key("000300", "指数"), "INDEX:000300")
        self.assertEqual(instrument_key("sh000300", "index"), "INDEX:000300")
        self.assertEqual(instrument_key("399006", "idx"), "INDEX:399006")

    def test_invalid_market_raises_value_error(self):
        with self.assertRaises(ValueError):
            instrument_key("600519", "火星")

    def test_invalid_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            instrument_key("abc", "A股")

    def test_none_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            instrument_key(None, "A股")


# ============================================================
# get_data dispatch (with mocks — no real network)
# ============================================================

class TestGetDataDispatch(unittest.TestCase):
    """Test that get_data dispatches to the correct market function."""

    def setUp(self):
        self.mock_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "open": [1.0] * 5,
            "high": [1.5] * 5,
            "low": [0.9] * 5,
            "close": [1.2] * 5,
            "volume": [1000] * 5,
        })

    @patch("src.backtest.data_feed.get_a_stock")
    def test_dispatches_to_a_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("600519", "A股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_a_stock")
    def test_a_stock_with_market_alias(self, mock_fn):
        """市场别名 'cn' 应分发到 get_a_stock。"""
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("600519", "cn", min_lookback_days=0)
        mock_fn.assert_called_once()
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "600519")

    @patch("src.backtest.data_feed.get_a_stock")
    def test_a_stock_normalizes_symbol_with_sh_prefix(self, mock_fn):
        mock_fn.return_value = self.mock_df
        data_feed.get_data("sh600519", "A股", min_lookback_days=0)
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "600519")

    @patch("src.backtest.data_feed.get_us_stock")
    def test_dispatches_to_us_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("AAPL", "美股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_us_stock")
    def test_us_stock_with_market_alias(self, mock_fn):
        """市场别名 'us' 应分发到 get_us_stock，且代码转为大写。"""
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("aapl", "us", min_lookback_days=0)
        mock_fn.assert_called_once()
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "AAPL")

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_dispatches_to_hk_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("00700", "港股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_hk_stock_with_market_alias(self, mock_fn):
        """市场别名 'hk' 应分发到 get_hk_stock，且补齐5位。"""
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("0700.HK", "hk", min_lookback_days=0)
        mock_fn.assert_called_once()
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "00700")

    @patch("src.backtest.data_feed.get_index_data")
    def test_dispatches_to_index(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("000300", "指数", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_index_data")
    def test_index_with_market_alias(self, mock_fn):
        """市场别名 'index' 应分发到 get_index_data。"""
        mock_fn.return_value = self.mock_df
        result = data_feed.get_data("sh000300", "index", min_lookback_days=0)
        mock_fn.assert_called_once()
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "000300")

    def test_invalid_market_raises_value_error(self):
        with self.assertRaises(ValueError):
            data_feed.get_data("600519", "火星", min_lookback_days=0)

    def test_invalid_symbol_raises_value_error(self):
        with self.assertRaises(ValueError):
            data_feed.get_data("", "A股", min_lookback_days=0)


if __name__ == "__main__":
    unittest.main()
