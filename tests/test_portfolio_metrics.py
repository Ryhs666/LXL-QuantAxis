"""Tests for portfolio return and risk metrics."""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.portfolio.metrics import (
    prices_to_returns,
    validate_weights,
    portfolio_return_series,
    cumulative_return,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    max_drawdown,
    PortfolioMetrics,
    summarize_portfolio,
)


# ============================================================
# 辅助
# ============================================================

def _make_price_df() -> pd.DataFrame:
    """3 资产、5 日的价格 DataFrame。"""
    return pd.DataFrame({
        "A": [100.0, 101.0, 102.0, 103.0, 104.0],
        "B": [50.0, 51.0, 49.5, 52.0, 53.0],
        "C": [200.0, 198.0, 202.0, 201.0, 205.0],
    })


def _make_return_df() -> pd.DataFrame:
    """3 资产、4 日的收益率 DataFrame。"""
    return pd.DataFrame({
        "A": [0.010, 0.009901, 0.009804, 0.009709],
        "B": [0.020, -0.029412, 0.050505, 0.019231],
        "C": [-0.010, 0.020202, -0.004950, 0.019900],
    })


# ============================================================
# prices_to_returns
# ============================================================

class TestPricesToReturns(unittest.TestCase):
    """测试价格转收益率。"""

    def setUp(self):
        self.prices = _make_price_df()

    def test_simple_returns_correct(self):
        r = prices_to_returns(self.prices, method="simple")
        self.assertEqual(r.shape, (4, 3))
        self.assertAlmostEqual(r["A"].iloc[0], 0.01)
        self.assertAlmostEqual(r["B"].iloc[0], 0.02)
        self.assertAlmostEqual(r["C"].iloc[0], -0.01)

    def test_log_returns_correct(self):
        r = prices_to_returns(self.prices, method="log")
        self.assertEqual(r.shape, (4, 3))
        expected = np.log(101.0 / 100.0)
        self.assertAlmostEqual(r["A"].iloc[0], expected)

    def test_columns_preserved(self):
        r = prices_to_returns(self.prices, method="simple")
        self.assertEqual(list(r.columns), ["A", "B", "C"])

    def test_original_not_modified(self):
        original = self.prices.copy()
        prices_to_returns(self.prices, method="simple")
        pd.testing.assert_frame_equal(self.prices, original)

    def test_invalid_method_raises(self):
        with self.assertRaises(ValueError):
            prices_to_returns(self.prices, method="arithmetic")

    def test_log_non_positive_price_raises(self):
        df = pd.DataFrame({"A": [100.0, 0.0, 50.0]})
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="log")

    def test_empty_dataframe_raises(self):
        with self.assertRaises(ValueError):
            prices_to_returns(pd.DataFrame(), method="simple")

    def test_non_numeric_column_raises(self):
        df = pd.DataFrame({"A": [100.0, 101.0], "B": ["x", "y"]})
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="simple")

    def test_duplicate_columns_raises(self):
        df = pd.DataFrame([[100.0, 50.0], [101.0, 51.0]], columns=["A", "A"])
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="simple")

    def test_non_dataframe_raises(self):
        with self.assertRaises(TypeError):
            prices_to_returns([1, 2, 3])

    # ---- 新增验证 ----

    def test_prices_with_nan_raises(self):
        df = pd.DataFrame({"A": [100.0, np.nan, 102.0]})
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="simple")

    def test_prices_with_inf_raises(self):
        df = pd.DataFrame({"A": [100.0, np.inf, 102.0]})
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="simple")

    def test_single_row_raises(self):
        df = pd.DataFrame({"A": [100.0]})
        with self.assertRaises(ValueError):
            prices_to_returns(df, method="simple")

    def test_method_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            prices_to_returns(self.prices, method=None)

    def test_method_int_raises_type_error(self):
        with self.assertRaises(TypeError):
            prices_to_returns(self.prices, method=42)


# ============================================================
# validate_weights
# ============================================================

class TestValidateWeights(unittest.TestCase):
    """测试权重校验。"""

    def test_valid_dict(self):
        w = validate_weights({"A": 0.5, "B": 0.3, "C": 0.2}, ["A", "B", "C"])
        self.assertIsInstance(w, pd.Series)
        self.assertEqual(list(w.index), ["A", "B", "C"])
        self.assertAlmostEqual(w["A"], 0.5)
        self.assertAlmostEqual(w["B"], 0.3)
        self.assertAlmostEqual(w["C"], 0.2)

    def test_aligned_to_assets_order(self):
        w = validate_weights({"C": 0.2, "A": 0.5, "B": 0.3}, ["A", "B", "C"])
        self.assertEqual(list(w.index), ["A", "B", "C"])
        self.assertAlmostEqual(w.iloc[0], 0.5)
        self.assertAlmostEqual(w.iloc[1], 0.3)
        self.assertAlmostEqual(w.iloc[2], 0.2)

    def test_missing_asset_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.5, "B": 0.5}, ["A", "B", "C"])

    def test_extra_asset_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}, ["A", "B", "C"])

    def test_sum_not_one_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.5, "B": 0.5, "C": 0.5}, ["A", "B", "C"])

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": -0.1, "B": 0.6, "C": 0.5}, ["A", "B", "C"])

    def test_nan_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": np.nan, "B": 0.5, "C": 0.5}, ["A", "B", "C"])

    def test_inf_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": np.inf, "B": 0.5, "C": 0.5}, ["A", "B", "C"])

    def test_series_input(self):
        w = pd.Series([0.5, 0.3, 0.2], index=["A", "B", "C"])
        result = validate_weights(w, ["A", "B", "C"])
        self.assertAlmostEqual(result.sum(), 1.0)

    def test_non_dict_type_raises(self):
        with self.assertRaises(TypeError):
            validate_weights([0.5, 0.5], ["A", "B"])

    def test_empty_assets_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 1.0}, [])

    # ---- 新增验证 ----

    def test_string_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": "0.5", "B": 0.5}, ["A", "B"])

    def test_bool_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": True, "B": False}, ["A", "B"])

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.5, "B": 0.5}, ["A", "B"], tolerance=-0.1)

    def test_nan_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.5, "B": 0.5}, ["A", "B"], tolerance=np.nan)

    def test_inf_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"A": 0.5, "B": 0.5}, ["A", "B"], tolerance=np.inf)


# ============================================================
# portfolio_return_series
# ============================================================

class TestPortfolioReturnSeries(unittest.TestCase):
    """测试组合加权收益率序列。"""

    def setUp(self):
        self.returns = _make_return_df()
        self.weights = {"A": 0.4, "B": 0.35, "C": 0.25}

    def test_correct_calculation(self):
        """手动验证第一行: 0.4*0.01 + 0.35*0.02 + 0.25*(-0.01) = 0.0085"""
        port = portfolio_return_series(self.returns, self.weights)
        self.assertAlmostEqual(port.iloc[0], 0.0085)

    def test_name_is_portfolio_return(self):
        port = portfolio_return_series(self.returns, self.weights)
        self.assertEqual(port.name, "portfolio_return")

    def test_preserves_index(self):
        port = portfolio_return_series(self.returns, self.weights)
        self.assertEqual(list(port.index), list(self.returns.index))

    def test_returns_not_modified(self):
        original = self.returns.copy()
        portfolio_return_series(self.returns, self.weights)
        pd.testing.assert_frame_equal(self.returns, original)

    def test_empty_returns_raises(self):
        with self.assertRaises(ValueError):
            portfolio_return_series(pd.DataFrame(), {"A": 1.0})

    def test_non_numeric_column_raises(self):
        df = pd.DataFrame({"A": [0.01, 0.02], "B": ["x", "y"]})
        with self.assertRaises(ValueError):
            portfolio_return_series(df, {"A": 0.5, "B": 0.5})

    def test_nan_in_returns_raises(self):
        df = pd.DataFrame({"A": [0.01, np.nan], "B": [0.02, 0.03]})
        with self.assertRaises(ValueError):
            portfolio_return_series(df, {"A": 0.5, "B": 0.5})

    def test_inf_in_returns_raises(self):
        df = pd.DataFrame({"A": [0.01, np.inf], "B": [0.02, 0.03]})
        with self.assertRaises(ValueError):
            portfolio_return_series(df, {"A": 0.5, "B": 0.5})


# ============================================================
# cumulative_return
# ============================================================

class TestCumulativeReturn(unittest.TestCase):
    """测试累计收益率。"""

    def test_compound(self):
        """两个 10% 的连续收益: (1.1)*(1.1) - 1 = 0.21"""
        r = pd.Series([0.1, 0.1], name="p")
        self.assertAlmostEqual(cumulative_return(r), 0.21)

    def test_negative(self):
        r = pd.Series([-0.1, 0.1], name="p")
        self.assertAlmostEqual(cumulative_return(r), -0.01)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            cumulative_return(pd.Series([], dtype=float))

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            cumulative_return(pd.Series([0.01, np.nan]))

    def test_inf_raises(self):
        with self.assertRaises(ValueError):
            cumulative_return(pd.Series([0.01, np.inf]))

    # ---- 新增验证 ----

    def test_return_below_minus_one_raises(self):
        r = pd.Series([0.01, -1.5], name="p")
        with self.assertRaises(ValueError):
            cumulative_return(r)


# ============================================================
# annualized_return
# ============================================================

class TestAnnualizedReturn(unittest.TestCase):
    """测试年化收益率。"""

    def test_basic(self):
        """每日 0.1% 收益，252 天，年化 ≈ (1.001)^252 - 1"""
        r = pd.Series([0.001] * 252, name="p")
        expected = (1.001 ** 252) - 1
        self.assertAlmostEqual(annualized_return(r, 252), expected, places=6)

    def test_negative_periods_raises(self):
        with self.assertRaises(ValueError):
            annualized_return(pd.Series([0.01] * 10), periods_per_year=-1)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            annualized_return(pd.Series([], dtype=float))

    # ---- 新增验证 ----

    def test_nan_raises(self):
        r = pd.Series([0.01, np.nan, 0.02])
        with self.assertRaises(ValueError):
            annualized_return(r)

    def test_inf_raises(self):
        r = pd.Series([0.01, np.inf, 0.02])
        with self.assertRaises(ValueError):
            annualized_return(r)

    def test_periods_per_year_nan_raises(self):
        r = pd.Series([0.01] * 10)
        with self.assertRaises(ValueError):
            annualized_return(r, periods_per_year=np.nan)

    def test_periods_per_year_inf_raises(self):
        r = pd.Series([0.01] * 10)
        with self.assertRaises(ValueError):
            annualized_return(r, periods_per_year=np.inf)


# ============================================================
# annualized_volatility
# ============================================================

class TestAnnualizedVolatility(unittest.TestCase):
    """测试年化波动率。"""

    def test_basic(self):
        r = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01], name="p")
        std = r.std(ddof=1)
        expected = std * np.sqrt(252)
        self.assertAlmostEqual(annualized_volatility(r, 252), expected)

    def test_less_than_two_obs_raises(self):
        with self.assertRaises(ValueError):
            annualized_volatility(pd.Series([0.01]))

    def test_negative_periods_raises(self):
        with self.assertRaises(ValueError):
            annualized_volatility(pd.Series([0.01, 0.02]), periods_per_year=0)

    # ---- 新增验证 ----

    def test_nan_raises(self):
        r = pd.Series([0.01, np.nan, 0.02])
        with self.assertRaises(ValueError):
            annualized_volatility(r)

    def test_inf_raises(self):
        r = pd.Series([0.01, np.inf, 0.02])
        with self.assertRaises(ValueError):
            annualized_volatility(r)


# ============================================================
# sharpe_ratio
# ============================================================

class TestSharpeRatio(unittest.TestCase):
    """测试夏普比率。"""

    def test_constant_returns_raises(self):
        """常数收益率（零波动）必须抛出 ValueError。"""
        r = pd.Series([0.001] * 252, name="p")
        with self.assertRaises(ValueError):
            sharpe_ratio(r, risk_free_rate=0.0, periods_per_year=252)

    def test_normal_positive_sharpe(self):
        """有波动的正收益应当返回有限的正常 Sharpe。"""
        rng = np.random.default_rng(42)
        r = pd.Series(rng.normal(0.001, 0.015, size=252), name="p")
        sr = sharpe_ratio(r, risk_free_rate=0.0, periods_per_year=252)
        self.assertTrue(np.isfinite(sr))
        self.assertGreater(sr, 0)

    def test_with_risk_free_rate_zero_volatility(self):
        """当全部收益等于无风险利率时，超额收益波动率为 0 → ValueError。"""
        rf = 0.05
        daily_rf = (1 + rf) ** (1 / 252) - 1  # 复利换算
        r = pd.Series([daily_rf] * 252, name="p")
        with self.assertRaises(ValueError):
            sharpe_ratio(r, risk_free_rate=rf, periods_per_year=252)

    def test_zero_volatility_raises(self):
        r = pd.Series([0.01, 0.01, 0.01], name="p")
        with self.assertRaises(ValueError):
            sharpe_ratio(r)

    def test_less_than_two_obs_raises(self):
        with self.assertRaises(ValueError):
            sharpe_ratio(pd.Series([0.01]))

    # ---- 新增验证 ----

    def test_nan_in_returns_raises(self):
        r = pd.Series([0.01, np.nan, 0.02])
        with self.assertRaises(ValueError):
            sharpe_ratio(r)

    def test_inf_in_returns_raises(self):
        r = pd.Series([0.01, np.inf, 0.02])
        with self.assertRaises(ValueError):
            sharpe_ratio(r)

    def test_returns_below_minus_one_raises(self):
        r = pd.Series([0.01, -1.5, 0.02])
        with self.assertRaises(ValueError):
            sharpe_ratio(r)

    def test_risk_free_rate_nan_raises(self):
        r = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01])
        with self.assertRaises(ValueError):
            sharpe_ratio(r, risk_free_rate=np.nan)

    def test_risk_free_rate_inf_raises(self):
        r = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01])
        with self.assertRaises(ValueError):
            sharpe_ratio(r, risk_free_rate=np.inf)

    def test_risk_free_rate_below_minus_one_raises(self):
        r = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01])
        with self.assertRaises(ValueError):
            sharpe_ratio(r, risk_free_rate=-2.0)

    def test_risk_free_rate_str_raises(self):
        r = pd.Series([0.01, -0.01, 0.02])
        with self.assertRaises(TypeError):
            sharpe_ratio(r, risk_free_rate="0.05")


# ============================================================
# max_drawdown
# ============================================================

class TestMaxDrawdown(unittest.TestCase):
    """测试最大回撤。"""

    def test_basic_drawdown(self):
        """先涨后跌: 100→110→99，回撤 = (99-110)/110 = -0.1"""
        r = pd.Series([0.10, -0.10], name="p")
        self.assertAlmostEqual(max_drawdown(r), -0.10)

    def test_all_time_rise(self):
        """全程上涨 → 最大回撤 0。"""
        r = pd.Series([0.01, 0.02, 0.01, 0.03], name="p")
        self.assertEqual(max_drawdown(r), 0.0)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            max_drawdown(pd.Series([], dtype=float))

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            max_drawdown(pd.Series([0.01, np.nan]))

    def test_severe_drawdown(self):
        """-50% 然后 +100% → 净值 1→0.5→1.0，最大回撤 -50%"""
        r = pd.Series([-0.5, 1.0], name="p")
        self.assertAlmostEqual(max_drawdown(r), -0.5)

    # ---- 新增验证 ----

    def test_return_below_minus_one_raises(self):
        r = pd.Series([0.01, -1.5])
        with self.assertRaises(ValueError):
            max_drawdown(r)


# ============================================================
# summarize_portfolio / PortfolioMetrics
# ============================================================

class TestSummarizePortfolio(unittest.TestCase):
    """测试 summarize_portfolio 和 PortfolioMetrics。"""

    def setUp(self):
        self.returns = _make_return_df()
        self.weights = {"A": 0.4, "B": 0.35, "C": 0.25}

    def test_returns_portfolio_metrics(self):
        m = summarize_portfolio(self.returns, self.weights)
        self.assertIsInstance(m, PortfolioMetrics)

    def test_dataclass_is_frozen(self):
        m = summarize_portfolio(self.returns, self.weights)
        with self.assertRaises(Exception):
            m.cumulative_return = 999.0

    def test_fields_present(self):
        m = summarize_portfolio(self.returns, self.weights)
        self.assertIsInstance(m.cumulative_return, float)
        self.assertIsInstance(m.annualized_return, float)
        self.assertIsInstance(m.annualized_volatility, float)
        self.assertIsInstance(m.sharpe_ratio, float)
        self.assertIsInstance(m.max_drawdown, float)
        self.assertIsInstance(m.observation_count, int)

    def test_observation_count(self):
        m = summarize_portfolio(self.returns, self.weights)
        self.assertEqual(m.observation_count, len(self.returns))

    def test_hand_calculable_two_asset_case(self):
        """手工可验证的双资产案例。"""
        prices = pd.DataFrame({
            "X": [100.0, 110.0, 121.0],
            "Y": [50.0, 47.0, 45.0],
        })
        r = prices_to_returns(prices, method="simple")
        w = {"X": 0.6, "Y": 0.4}

        port = portfolio_return_series(r, w)
        self.assertAlmostEqual(port.iloc[0], 0.036)
        expected_day2 = 0.6 * 0.10 + 0.4 * (-2.0 / 47.0)
        self.assertAlmostEqual(port.iloc[1], expected_day2)

        cum = cumulative_return(port)
        manual_cum = (1 + port.iloc[0]) * (1 + port.iloc[1]) - 1
        self.assertAlmostEqual(cum, manual_cum)

        m = summarize_portfolio(r, w, periods_per_year=252)
        self.assertEqual(m.observation_count, 2)
        self.assertAlmostEqual(m.cumulative_return, manual_cum)

    def test_inputs_not_modified(self):
        r_orig = self.returns.copy()
        w_orig = dict(self.weights)
        summarize_portfolio(self.returns, self.weights)
        pd.testing.assert_frame_equal(self.returns, r_orig)
        self.assertEqual(self.weights, w_orig)

    def test_with_specified_risk_free_rate(self):
        m = summarize_portfolio(self.returns, self.weights, risk_free_rate=0.03)
        self.assertIsInstance(m, PortfolioMetrics)

    # ---- 新增验证 ----

    def test_risk_free_rate_below_minus_one_raises(self):
        with self.assertRaises(ValueError):
            summarize_portfolio(self.returns, self.weights, risk_free_rate=-2.0)


# ============================================================
# 兼容性测试：确保原有 PortfolioManager 导入路径未被破坏
# ============================================================

class TestPortfolioInitCompatibility(unittest.TestCase):
    """验证 src/portfolio/__init__.py 的向后兼容性。"""

    def test_portfolio_manager_importable(self):
        """from src.portfolio import PortfolioManager 必须成功。"""
        from src.portfolio import PortfolioManager as PM
        self.assertTrue(callable(getattr(PM, "__init__", None)))

    def test_new_metrics_importable(self):
        """新增指标函数可从顶层包导入。"""
        from src.portfolio import (
            summarize_portfolio,
            cumulative_return,
            annualized_return,
            annualized_volatility,
            sharpe_ratio,
            max_drawdown,
        )
        self.assertTrue(callable(summarize_portfolio))
        self.assertTrue(callable(cumulative_return))
        self.assertTrue(callable(annualized_return))
        self.assertTrue(callable(annualized_volatility))
        self.assertTrue(callable(sharpe_ratio))
        self.assertTrue(callable(max_drawdown))


if __name__ == "__main__":
    unittest.main()
