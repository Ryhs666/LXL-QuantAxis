"""Tests for src.lxl_quantaxis.portfolio.allocation — allocation models + walk-forward."""

import numpy as np
import pandas as pd
import pytest
from src.lxl_quantaxis.portfolio.allocation import (
    _validate_returns_matrix,
    equal_weight,
    inverse_volatility,
    risk_parity,
    mean_variance,
    hierarchical_risk_parity,
    walk_forward,
    walk_forward_summary,
    WalkForwardWindow,
)


def _make_returns(n_assets=3, n_periods=500, seed=42):
    rng = np.random.default_rng(seed)
    data = rng.normal(0.0005, 0.015, (n_periods, n_assets))
    cols = [f"asset_{i}" for i in range(n_assets)]
    idx = pd.date_range("2024-01-01", periods=n_periods, freq="B")
    return pd.DataFrame(data, index=idx, columns=cols)


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class TestValidation:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _validate_returns_matrix(pd.DataFrame())

    def test_too_few_periods(self):
        rets = _make_returns(n_periods=5)
        with pytest.raises(ValueError):
            _validate_returns_matrix(rets, min_periods=20)

    def test_duplicate_columns(self):
        rets = _make_returns()
        rets.columns = ["a", "b", "a"]
        with pytest.raises(ValueError, match="duplicate"):
            _validate_returns_matrix(rets)

    def test_non_datetime_index(self):
        rets = pd.DataFrame({"a": [0.01]*25, "b": [0.02]*25})
        with pytest.raises(TypeError):
            _validate_returns_matrix(rets)

    def test_duplicate_dates(self):
        idx = pd.date_range("2024-01-01", periods=100, freq="B")
        dup = idx.tolist()[:2] + idx.tolist()[2:]
        dup[1] = dup[0]  # duplicate first date
        rets = pd.DataFrame({"a": np.random.randn(100), "b": np.random.randn(100)},
                            index=pd.DatetimeIndex(dup))
        with pytest.raises(ValueError, match="duplicate"):
            _validate_returns_matrix(rets)

    def test_nan_raises(self):
        rets = _make_returns()
        rets.iloc[0, 0] = np.nan
        with pytest.raises(ValueError, match="NaN"):
            _validate_returns_matrix(rets)


# ═══════════════════════════════════════════════════════════
# Equal weight
# ═══════════════════════════════════════════════════════════

class TestEqualWeight:
    def test_basic(self):
        rets = _make_returns(n_assets=4)
        w = equal_weight(rets)
        assert len(w) == 4
        assert abs(w.sum() - 1.0) < 1e-8
        assert (w >= 0).all()

    def test_single_asset(self):
        rets = _make_returns(n_assets=1)
        w = equal_weight(rets)
        assert w.iloc[0] == 1.0


# ═══════════════════════════════════════════════════════════
# Inverse volatility
# ═══════════════════════════════════════════════════════════

class TestInverseVolatility:
    def test_basic(self):
        rets = _make_returns()
        w = inverse_volatility(rets)
        assert len(w) == 3
        assert abs(w.sum() - 1.0) < 1e-8


# ═══════════════════════════════════════════════════════════
# Risk parity
# ═══════════════════════════════════════════════════════════

class TestRiskParity:
    def test_weights_sum_to_one(self):
        rets = _make_returns()
        w = risk_parity(rets)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_weights_non_negative(self):
        rets = _make_returns()
        w = risk_parity(rets)
        assert (w >= 0).all()

    def test_single_asset(self):
        rets = _make_returns(n_assets=1)
        w = risk_parity(rets)
        assert w.iloc[0] == 1.0

    def test_deterministic(self):
        rets = _make_returns()
        w1 = risk_parity(rets)
        w2 = risk_parity(rets)
        pd.testing.assert_series_equal(w1, w2)


# ═══════════════════════════════════════════════════════════
# Mean-variance
# ═══════════════════════════════════════════════════════════

class TestMeanVariance:
    def test_basic(self):
        rets = _make_returns()
        w = mean_variance(rets)
        assert len(w) == 3
        assert abs(w.sum() - 1.0) < 1e-6
        assert (w >= 0).all()

    def test_single_asset(self):
        rets = _make_returns(n_assets=1)
        w = mean_variance(rets)
        assert w.iloc[0] == 1.0


# ═══════════════════════════════════════════════════════════
# HRP
# ═══════════════════════════════════════════════════════════

class TestHRP:
    def test_weights_sum_to_one(self):
        rets = _make_returns()
        w = hierarchical_risk_parity(rets)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_weights_non_negative(self):
        rets = _make_returns()
        w = hierarchical_risk_parity(rets)
        assert (w >= 0).all()

    def test_single_asset(self):
        rets = _make_returns(n_assets=1)
        w = hierarchical_risk_parity(rets)
        assert w.iloc[0] == 1.0

    def test_deterministic(self):
        rets = _make_returns()
        w1 = hierarchical_risk_parity(rets)
        w2 = hierarchical_risk_parity(rets)
        pd.testing.assert_series_equal(w1, w2)

    def test_different_from_equal(self):
        """HRP should not just be equal weight for diversified assets."""
        # Create assets with different volatilities
        rng = np.random.default_rng(99)
        rets = pd.DataFrame({
            "low_vol": rng.normal(0.0005, 0.005, 500),
            "high_vol": rng.normal(0.0005, 0.025, 500),
        }, index=pd.date_range("2024-01-01", periods=500, freq="B"))
        w = hierarchical_risk_parity(rets)
        # Lower vol asset should get higher weight
        assert w["low_vol"] > w["high_vol"]


# ═══════════════════════════════════════════════════════════
# Walk-forward
# ═══════════════════════════════════════════════════════════

class TestWalkForward:
    def test_produces_windows(self):
        rets = _make_returns(n_periods=400)
        windows = walk_forward(rets, model="equal", train_window=200, test_window=50)
        assert len(windows) >= 3

    def test_no_overlap(self):
        rets = _make_returns(n_periods=400)
        windows = walk_forward(rets, train_window=200, test_window=50)
        for i in range(len(windows) - 1):
            assert windows[i].test_end <= windows[i + 1].test_start

    def test_train_before_test(self):
        rets = _make_returns(n_periods=400)
        windows = walk_forward(rets, model="risk_parity", train_window=200, test_window=50)
        for w in windows:
            assert w.train_end <= w.test_start

    def test_insufficient_data(self):
        rets = _make_returns(n_periods=100)
        with pytest.raises(ValueError):
            walk_forward(rets, train_window=300, test_window=50)

    def test_summary(self):
        rets = _make_returns(n_periods=400)
        windows = walk_forward(rets, model="risk_parity", train_window=200, test_window=50)
        summary = walk_forward_summary(windows)
        assert summary["windows"] >= 3
        assert "total_test_return" in summary

    def test_weights_order_matches_input(self):
        rets = _make_returns(n_assets=3, n_periods=400)
        windows = walk_forward(rets, model="equal", train_window=200, test_window=50)
        first_weights = list(windows[0].weights.keys())
        assert first_weights == list(rets.columns)

    def test_invalid_model_raises(self):
        rets = _make_returns(n_periods=400)
        with pytest.raises(ValueError, match="unknown model"):
            walk_forward(rets, model="nonexistent")
