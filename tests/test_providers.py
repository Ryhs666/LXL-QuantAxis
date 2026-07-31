"""Tests for unified market data provider interface."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.providers import (
    MarketDataProvider,
    CallableDataProvider,
    ProviderRegistry,
)
from src.backtest.data_feed import (
    get_data,
    get_provider_registry,
    register_data_provider,
)
from src.backtest.symbols import normalize_market


# ============================================================
# 辅助
# ============================================================

def _make_sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5),
        "open": [1.0] * 5,
        "high": [1.5] * 5,
        "low": [0.9] * 5,
        "close": [1.2] * 5,
        "volume": [1000] * 5,
    })


# ============================================================
# 测试 1 & 2: 默认市场注册 + 别名获取
# ============================================================

class TestDefaultRegistry(unittest.TestCase):
    """测试默认注册表的四个市场及其别名。"""

    @classmethod
    def setUpClass(cls):
        cls.registry = get_provider_registry()

    def test_four_markets_registered(self):
        markets = self.registry.markets()
        self.assertEqual(len(markets), 4)
        self.assertIn("A股", markets)
        self.assertIn("美股", markets)
        self.assertIn("港股", markets)
        self.assertIn("指数", markets)

    def test_markets_order_stable(self):
        """markets() 多次调用返回顺序一致。"""
        m1 = self.registry.markets()
        m2 = self.registry.markets()
        self.assertEqual(m1, m2)

    # ---- 别名获取 ----

    def test_get_a_share_by_alias(self):
        for alias in ["A股", "A", "CN", "CHINA", "cn", "china"]:
            with self.subTest(alias=alias):
                p = self.registry.get(alias)
                self.assertEqual(p.market, "A股")

    def test_get_us_by_alias(self):
        for alias in ["美股", "US", "USA", "us", "usa"]:
            with self.subTest(alias=alias):
                p = self.registry.get(alias)
                self.assertEqual(p.market, "美股")

    def test_get_hk_by_alias(self):
        for alias in ["港股", "HK", "HONGKONG", "hk", "hongkong"]:
            with self.subTest(alias=alias):
                p = self.registry.get(alias)
                self.assertEqual(p.market, "港股")

    def test_get_index_by_alias(self):
        for alias in ["指数", "INDEX", "IDX", "index", "idx"]:
            with self.subTest(alias=alias):
                p = self.registry.get(alias)
                self.assertEqual(p.market, "指数")

    def test_default_provider_names(self):
        self.assertEqual(self.registry.get("A股").name, "akshare")
        self.assertEqual(self.registry.get("美股").name, "yfinance")
        self.assertEqual(self.registry.get("港股").name, "akshare")
        self.assertEqual(self.registry.get("指数").name, "akshare")


# ============================================================
# 测试 3-6: 注册表逻辑（独立实例，不污染默认表）
# ============================================================

class TestProviderRegistryLogic(unittest.TestCase):
    """使用独立 ProviderRegistry 测试核心逻辑。"""

    def setUp(self):
        self.registry = ProviderRegistry()
        self.provider = CallableDataProvider(
            name="test", market="A股", fetcher=lambda **kw: None
        )

    def test_register_ok(self):
        self.registry.register(self.provider)
        self.assertIn("A股", self.registry.markets())

    def test_duplicate_register_raises(self):
        self.registry.register(self.provider)
        p2 = CallableDataProvider(name="test2", market="A股", fetcher=lambda **kw: None)
        with self.assertRaises(ValueError):
            self.registry.register(p2)

    def test_replace_allows_override(self):
        self.registry.register(self.provider)
        p2 = CallableDataProvider(name="replacement", market="A股", fetcher=lambda **kw: None)
        self.registry.register(p2, replace=True)
        self.assertEqual(self.registry.get("A股").name, "replacement")

    def test_unknown_market_raises(self):
        with self.assertRaises(ValueError):
            self.registry.get("火星")

    def test_register_non_provider_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.registry.register("not a provider")
        with self.assertRaises(TypeError):
            self.registry.register(42)
        with self.assertRaises(TypeError):
            self.registry.register(object())

    def test_fresh_registry_empty_markets(self):
        self.assertEqual(self.registry.markets(), [])

    def test_register_multiple_markets(self):
        p_a = CallableDataProvider(name="a", market="A股", fetcher=lambda **kw: None)
        p_us = CallableDataProvider(name="us", market="US", fetcher=lambda **kw: None)
        self.registry.register(p_a)
        self.registry.register(p_us)
        self.assertEqual(len(self.registry.markets()), 2)
        self.assertIn("A股", self.registry.markets())
        self.assertIn("美股", self.registry.markets())


# ============================================================
# 测试 7 & 8: CallableDataProvider
# ============================================================

class TestCallableDataProvider(unittest.TestCase):
    """测试 CallableDataProvider 的参数转发和返回值。"""

    def setUp(self):
        self.sample_df = _make_sample_df()

    def test_forwards_all_parameters(self):
        """验证全部四个参数被正确转发。"""
        received = {}

        def capture(symbol, start_date, end_date, use_cache):
            received["symbol"] = symbol
            received["start_date"] = start_date
            received["end_date"] = end_date
            received["use_cache"] = use_cache
            return self.sample_df

        provider = CallableDataProvider(name="test", market="A股", fetcher=capture)
        result = provider.fetch("600519", "2024-01-01", "2024-12-31", use_cache=False)

        self.assertEqual(received["symbol"], "600519")
        self.assertEqual(received["start_date"], "2024-01-01")
        self.assertEqual(received["end_date"], "2024-12-31")
        self.assertIs(received["use_cache"], False)
        self.assertIs(result, self.sample_df)

    def test_returns_dataframe(self):
        provider = CallableDataProvider(
            name="test", market="A股",
            fetcher=lambda symbol, start_date, end_date, use_cache: self.sample_df,
        )
        result = provider.fetch("600519", "2024-01-01")
        self.assertIsInstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, self.sample_df)

    def test_end_date_defaults_to_none(self):
        received = {}

        def capture(symbol, start_date, end_date, use_cache):
            received["end_date"] = end_date
            received["use_cache"] = use_cache
            return self.sample_df

        provider = CallableDataProvider(name="test", market="A股", fetcher=capture)
        provider.fetch("600519", "2024-01-01")
        self.assertIsNone(received["end_date"])
        self.assertIs(received["use_cache"], True)

    def test_market_is_normalized(self):
        provider = CallableDataProvider(
            name="test", market="cn",
            fetcher=lambda **kw: self.sample_df,
        )
        self.assertEqual(provider.market, "A股")

    def test_non_callable_fetcher_raises(self):
        with self.assertRaises(TypeError):
            CallableDataProvider(name="bad", market="A股", fetcher="not_callable")


# ============================================================
# 测试 9 & 10: get_data 通过 Registry 分发 + patch 兼容
# ============================================================

class TestGetDataDispatch(unittest.TestCase):
    """验证 get_data 通过 ProviderRegistry 正确分发，且 patch 仍有效。"""

    def setUp(self):
        self.mock_df = _make_sample_df()

    # ---- 四个市场分发 ----

    @patch("src.backtest.data_feed.get_a_stock")
    def test_dispatches_to_a_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = get_data("600519", "A股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_a_stock")
    def test_a_stock_normalizes_symbol(self, mock_fn):
        """验证代码在 lambda 调用前已被标准化。"""
        mock_fn.return_value = self.mock_df
        get_data("sh600519", "A股", min_lookback_days=0)
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "600519")

    @patch("src.backtest.data_feed.get_us_stock")
    def test_dispatches_to_us_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = get_data("AAPL", "美股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_us_stock")
    def test_us_stock_with_alias(self, mock_fn):
        mock_fn.return_value = self.mock_df
        get_data("aapl", "us", min_lookback_days=0)
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "AAPL")

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_dispatches_to_hk_stock(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = get_data("00700", "港股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_hk_stock_with_alias(self, mock_fn):
        mock_fn.return_value = self.mock_df
        get_data("0700.HK", "hk", min_lookback_days=0)
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "00700")

    @patch("src.backtest.data_feed.get_index_data")
    def test_dispatches_to_index(self, mock_fn):
        mock_fn.return_value = self.mock_df
        result = get_data("000300", "指数", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_index_data")
    def test_index_with_alias(self, mock_fn):
        mock_fn.return_value = self.mock_df
        get_data("sh000300", "index", min_lookback_days=0)
        call_args = mock_fn.call_args
        self.assertEqual(call_args[0][0], "000300")

    # ---- patch 兼容性 ----

    @patch("src.backtest.data_feed.get_a_stock")
    def test_patch_compatibility_a_stock(self, mock_fn):
        """Commit 3B 的 patch 方式仍然有效。"""
        mock_fn.return_value = self.mock_df
        result = get_data("600519", "A股", min_lookback_days=0)
        mock_fn.assert_called_once()
        self.assertIs(result, self.mock_df)

    @patch("src.backtest.data_feed.get_us_stock")
    def test_patch_compatibility_us_stock(self, mock_fn):
        """验证美股 patch 兼容。"""
        mock_fn.return_value = self.mock_df
        result = get_data("aapl", "us", min_lookback_days=0)
        mock_fn.assert_called_once()

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_patch_compatibility_hk_stock(self, mock_fn):
        """验证港股 patch 兼容。"""
        mock_fn.return_value = self.mock_df
        result = get_data("00700", "hk", min_lookback_days=0)
        mock_fn.assert_called_once()

    @patch("src.backtest.data_feed.get_index_data")
    def test_patch_compatibility_index(self, mock_fn):
        """验证指数 patch 兼容。"""
        mock_fn.return_value = self.mock_df
        result = get_data("000300", "index", min_lookback_days=0)
        mock_fn.assert_called_once()


# ============================================================
# 测试 11: 自定义 Provider
# ============================================================

class TestCustomProvider(unittest.TestCase):
    """测试自定义 Provider 的注册与调用，测试后恢复默认注册表。"""

    def setUp(self):
        self.registry = get_provider_registry()
        # 保存原始 A股 provider
        self._saved_a_stock = self.registry.get("A股")
        self.mock_df = _make_sample_df()

    def tearDown(self):
        # 恢复原始 A股 provider
        try:
            self.registry.register(self._saved_a_stock, replace=True)
        except Exception:
            pass

    def test_custom_provider_registered_and_called(self):
        """自定义 Provider 注册后，get_data 应使用新 Provider。"""
        called_with = {}

        def custom_fetcher(symbol, start_date, end_date, use_cache):
            called_with["symbol"] = symbol
            return self.mock_df

        custom = CallableDataProvider(name="custom", market="A股", fetcher=custom_fetcher)
        register_data_provider(custom, replace=True)

        # 验证注册已替换
        self.assertEqual(self.registry.get("A股").name, "custom")

        # 验证 get_data 使用自定义 provider
        result = get_data("600519", "A股", min_lookback_days=0)
        self.assertIs(result, self.mock_df)
        self.assertEqual(called_with.get("symbol"), "600519")

    def test_custom_provider_via_registry_direct(self):
        """直接通过 register_data_provider 注册全部四个市场后再恢复。"""
        # 保存所有
        saved = {m: self.registry.get(m) for m in self.registry.markets()}

        try:
            # 注册自定义 provider 替换 A股
            custom = CallableDataProvider(
                name="custom2", market="A股",
                fetcher=lambda **kw: self.mock_df,
            )
            register_data_provider(custom, replace=True)
            self.assertEqual(self.registry.get("A股").name, "custom2")
        finally:
            # 恢复所有
            for m, p in saved.items():
                self.registry.register(p, replace=True)


if __name__ == "__main__":
    unittest.main()
