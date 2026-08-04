"""Tests for src.lxl_quantaxis.portfolio.analytics — explicit-semantics metrics."""

import math
import numpy as np
import pandas as pd
import pytest
from src.lxl_quantaxis.portfolio.analytics import (
    ReturnType,
    RebalanceMode,
    PortfolioMetrics,
    cumulative_return,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    max_drawdown,
    calmar_ratio,
    portfolio_return_series,
    summarize,
)


# ── Helper ──────────────────────────────────────────────

def _make_returns(values: list, return_type=ReturnType.SIMPLE) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="B"),
                     name="asset")


# ═══════════════════════════════════════════════════════════
# cumulative_return
# ═══════════════════════════════════════════════════════════

class TestCumulativeReturn:
    def test_simple_compound(self):
        # 100 → 110 → 121  = +21%
        r = _make_returns([0.10, 0.10])
        assert cumulative_return(r, ReturnType.SIMPLE) == pytest.approx(0.21)

    def test_log_compound(self):
        # log returns: ln(110/100)=0.09531, ln(121/110)=0.09531
        r = _make_returns([math.log(1.10), math.log(1.10)], ReturnType.LOG)
        result = cumulative_return(r, ReturnType.LOG)
        assert result == pytest.approx(0.21)

    def test_log_vs_simple_not_equal(self):
        r = _make_returns([0.10, 0.10])
        simple_val = cumulative_return(r, ReturnType.SIMPLE)
        # Passing SIMPLE returns to LOG function should give WRONG answer
        log_val = cumulative_return(r, ReturnType.LOG)
        assert not math.isclose(simple_val, log_val, rel_tol=0.01)

    def test_single_observation(self):
        r = _make_returns([0.05])
        assert cumulative_return(r, ReturnType.SIMPLE) == pytest.approx(0.05)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            cumulative_return(pd.Series([], dtype=float), ReturnType.SIMPLE)

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            cumulative_return(_make_returns([0.01, np.nan]), ReturnType.SIMPLE)

    def test_inf_raises(self):
        with pytest.raises(ValueError):
            cumulative_return(_make_returns([0.01, np.inf]), ReturnType.SIMPLE)

    def test_below_minus_one_raises(self):
        with pytest.raises(ValueError):
            cumulative_return(_make_returns([0.01, -1.5]), ReturnType.SIMPLE)

    def test_all_negative(self):
        r = _make_returns([-0.02, -0.03, -0.01])
        result = cumulative_return(r, ReturnType.SIMPLE)
        assert result < 0
        assert result > -1


# ═══════════════════════════════════════════════════════════
# annualized_return
# ═══════════════════════════════════════════════════════════

class TestAnnualizedReturn:
    def test_basic(self):
        r = _make_returns([0.001] * 252)
        ann = annualized_return(r, ReturnType.SIMPLE, periods_per_year=252)
        assert ann > 0

    def test_negative_periods_raises(self):
        r = _make_returns([0.01] * 10)
        with pytest.raises(ValueError):
            annualized_return(r, ReturnType.SIMPLE, periods_per_year=-1)

    def test_bool_raises(self):
        r = _make_returns([0.01] * 10)
        with pytest.raises(TypeError):
            annualized_return(r, ReturnType.SIMPLE, periods_per_year=True)


# ═══════════════════════════════════════════════════════════
# sharpe_ratio
# ═══════════════════════════════════════════════════════════

class TestSharpeRatio:
    def test_positive_sharpe(self):
        r = _make_returns([0.001] * 252 + [0.002] * 252)
        sr = sharpe_ratio(r, ReturnType.SIMPLE, risk_free_rate=0.0)
        assert sr is not None and sr > 0

    def test_zero_vol_returns_none(self):
        r = _make_returns([0.001] * 100)
        sr = sharpe_ratio(r, ReturnType.SIMPLE)
        assert sr is None

    def test_bool_risk_free_raises(self):
        r = _make_returns([0.001] * 100 + [0.002] * 100)
        with pytest.raises(TypeError):
            sharpe_ratio(r, ReturnType.SIMPLE, risk_free_rate=True)

    def test_inf_risk_free_raises(self):
        r = _make_returns([0.001] * 100 + [0.002] * 100)
        with pytest.raises(ValueError):
            sharpe_ratio(r, ReturnType.SIMPLE, risk_free_rate=np.inf)


# ═══════════════════════════════════════════════════════════
# max_drawdown
# ═══════════════════════════════════════════════════════════

class TestMaxDrawdown:
    def test_basic(self):
        r = _make_returns([0.02, -0.05, 0.01])
        dd = max_drawdown(r)
        assert dd <= 0

    def test_all_rise_zero_dd(self):
        r = _make_returns([0.01, 0.02, 0.03])
        assert max_drawdown(r) == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════
# portfolio_return_series
# ═══════════════════════════════════════════════════════════

class TestPortfolioReturnSeries:
    def test_periodic_simple(self):
        rets = pd.DataFrame({
            "A": [0.10, -0.05],
            "B": [0.00, 0.00],
        }, index=pd.date_range("2024-01-01", periods=2, freq="B"))
        w = pd.Series({"A": 0.5, "B": 0.5})
        port = portfolio_return_series(rets, w, rebalance_mode=RebalanceMode.PERIODIC)
        assert len(port) == 2
        assert port.iloc[0] == pytest.approx(0.05)  # 0.5*0.10 + 0.5*0

    def test_buy_and_hold_drift(self):
        # A up 100% then down 50%: final = 100% * 200% * 50% = 100% (0% total)
        # B flat
        rets = pd.DataFrame({
            "A": [1.00, -0.50],
            "B": [0.00, 0.00],
        }, index=pd.date_range("2024-01-01", periods=2, freq="B"))
        w = pd.Series({"A": 0.5, "B": 0.5})
        port_bh = portfolio_return_series(rets, w, rebalance_mode=RebalanceMode.BUY_AND_HOLD)
        port_rb = portfolio_return_series(rets, w, rebalance_mode=RebalanceMode.PERIODIC)
        # BH and periodic give different results
        assert not math.isclose(port_bh.sum(), port_rb.sum(), rel_tol=0.001)

    def test_missing_asset_raises(self):
        rets = pd.DataFrame({"A": [0.01]}, index=pd.date_range("2024-01-01", periods=1, freq="B"))
        w = pd.Series({"A": 0.5, "B": 0.5})
        with pytest.raises(ValueError, match="B"):
            portfolio_return_series(rets, w)

    def test_negative_weight_raises(self):
        rets = pd.DataFrame({"A": [0.01], "B": [0.02]},
                            index=pd.date_range("2024-01-01", periods=1, freq="B"))
        w = pd.Series({"A": 0.6, "B": -0.6, "C": 1.0})
        w2 = pd.Series({"A": 1.5, "B": -0.5})
        with pytest.raises(ValueError, match="long-only"):
            portfolio_return_series(rets, w2)

    def test_weights_not_sum_one_raises(self):
        rets = pd.DataFrame({"A": [0.01], "B": [0.02]},
                            index=pd.date_range("2024-01-01", periods=1, freq="B"))
        w = pd.Series({"A": 0.3, "B": 0.3})
        with pytest.raises(ValueError):
            portfolio_return_series(rets, w)


# ═══════════════════════════════════════════════════════════
# summarize
# ═══════════════════════════════════════════════════════════

class TestSummarize:
    def test_returns_portfolio_metrics(self):
        rets = pd.DataFrame({
            "A": np.random.randn(252) * 0.01 + 0.0005,
            "B": np.random.randn(252) * 0.015 + 0.0003,
        }, index=pd.date_range("2024-01-01", periods=252, freq="B"))
        w = pd.Series({"A": 0.6, "B": 0.4})
        pm = summarize(rets, w, ReturnType.SIMPLE, RebalanceMode.PERIODIC)
        assert isinstance(pm, PortfolioMetrics)
        assert pm.observation_count == 252
        assert pm.return_type == ReturnType.SIMPLE
        assert pm.total_return is not None

    def test_frozen_dataclass(self):
        rets = pd.DataFrame({"A": [0.01, 0.02]},
                            index=pd.date_range("2024-01-01", periods=2, freq="B"))
        w = pd.Series({"A": 1.0})
        pm = summarize(rets, w, ReturnType.SIMPLE, RebalanceMode.PERIODIC)
        with pytest.raises(Exception):  # frozen
            pm.total_return = 0.5  # type: ignore

    def test_single_asset(self):
        rets = pd.DataFrame({"A": [0.01, 0.02]},
                            index=pd.date_range("2024-01-01", periods=2, freq="B"))
        w = pd.Series({"A": 1.0})
        pm = summarize(rets, w, ReturnType.SIMPLE, RebalanceMode.PERIODIC)
        assert pm.total_return == pytest.approx(0.0302)

    def test_duplicate_dates_raises(self):
        idx = pd.DatetimeIndex(["2024-01-01", "2024-01-01"])
        rets = pd.DataFrame({"A": [0.01, 0.02]}, index=idx)
        w = pd.Series({"A": 1.0})
        with pytest.raises(ValueError):
            summarize(rets, w)

    def test_unordered_dates_raises(self):
        idx = pd.DatetimeIndex(["2024-01-03", "2024-01-01"])
        rets = pd.DataFrame({"A": [0.01, 0.02]}, index=idx)
        w = pd.Series({"A": 1.0})
        with pytest.raises(ValueError):
            summarize(rets, w)
