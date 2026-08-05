"""Tests for portfolio intelligence layer."""

import pytest
from src.lxl_quantaxis.portfolio.intelligence import (
    StrategyProfile, PortfolioAssessment,
    assess_portfolio,
    _allocate_equal, _allocate_risk_weighted, _allocate_sharpe_weighted,
    _compute_factor_exposure, _compute_correlation_warning,
    _compute_diversification_score,
)


def _make_strategies():
    return [
        {"name": "growth_momentum", "expected_return": 15.0, "risk": 18.0,
         "max_drawdown": -15.0, "sharpe": 1.2,
         "factor_exposure": {"momentum_score": 0.4, "roc_10": 0.3, "trend_strength": 0.3}},
        {"name": "value_mean_reversion", "expected_return": 8.0, "risk": 10.0,
         "max_drawdown": -8.0, "sharpe": 0.8,
         "factor_exposure": {"ma_deviation": 0.4, "bollinger_pos": 0.3, "volatility": 0.3}},
        {"name": "trend_following", "expected_return": 12.0, "risk": 15.0,
         "max_drawdown": -12.0, "sharpe": 1.0,
         "factor_exposure": {"ma_slope": 0.4, "trend_strength": 0.4}},
    ]


class TestAllocation:
    def test_equal_weight(self):
        profiles = [StrategyProfile(name=f"s{i}") for i in range(3)]
        result = _allocate_equal(profiles)
        for p in result:
            assert abs(p.allocation - 1.0 / 3) < 0.01

    def test_risk_weighted(self):
        profiles = [
            StrategyProfile(name="low_risk", risk=5.0),
            StrategyProfile(name="high_risk", risk=20.0),
        ]
        result = _allocate_risk_weighted(profiles)
        assert result[0].allocation > result[1].allocation

    def test_sharpe_weighted(self):
        profiles = [
            StrategyProfile(name="good", sharpe=2.0),
            StrategyProfile(name="bad", sharpe=0.2),
        ]
        result = _allocate_sharpe_weighted(profiles)
        assert result[0].allocation > result[1].allocation

    def test_weights_sum_to_one(self):
        profiles = [StrategyProfile(name=f"s{i}") for i in range(5)]
        for fn in [_allocate_equal, _allocate_risk_weighted, _allocate_sharpe_weighted]:
            result = fn([StrategyProfile(name=f"s{i}", risk=10, sharpe=1)
                         for i in range(5)])
            assert abs(sum(p.allocation for p in result) - 1.0) < 0.01


class TestFactorExposure:
    def test_computes_weighted_exposure(self):
        profiles = [
            StrategyProfile(name="a", allocation=0.5,
                            factor_exposure={"momentum_score": 0.8}),
            StrategyProfile(name="b", allocation=0.5,
                            factor_exposure={"momentum_score": 0.2}),
        ]
        exp = _compute_factor_exposure(profiles)
        assert abs(exp["momentum_score"] - 0.5) < 0.01

    def test_empty_profiles(self):
        assert _compute_factor_exposure([]) == {}


class TestRiskWarnings:
    def test_single_strategy(self):
        profiles = [StrategyProfile(name="only")]
        w = _compute_correlation_warning(profiles)
        assert "单一" in w

    def test_highly_correlated(self):
        profiles = [
            StrategyProfile(name="a", factor_exposure={"momentum_score": 0.8}),
            StrategyProfile(name="b", factor_exposure={"momentum_score": 0.7}),
            StrategyProfile(name="c", factor_exposure={"momentum_score": 0.6}),
        ]
        w = _compute_correlation_warning(profiles)
        assert "集中" in w or "成长" in w


class TestDiversification:
    def test_identical_strategies(self):
        profiles = [
            StrategyProfile(name="a", factor_exposure={"momentum_score": 0.5}),
            StrategyProfile(name="b", factor_exposure={"momentum_score": 0.5}),
        ]
        score = _compute_diversification_score(profiles)
        assert score < 0.5  # identical → low diversity

    def test_diverse_strategies(self):
        profiles = [
            StrategyProfile(name="a", factor_exposure={"momentum_score": 0.5}),
            StrategyProfile(name="b", factor_exposure={"ma_deviation": 0.5}),
        ]
        score = _compute_diversification_score(profiles)
        assert score > 0.5


class TestAssessPortfolio:
    def test_full_assessment(self):
        result = assess_portfolio(_make_strategies(), method="risk_weighted")
        assert len(result.allocation) == 3
        assert result.expected_return != 0
        assert result.diversification_score >= 0
        assert result.source == "rule"

    def test_equal_allocation(self):
        result = assess_portfolio(_make_strategies(), method="equal")
        weights = [a["weight"] for a in result.allocation]
        assert abs(sum(weights) - 1.0) < 0.01

    def test_empty_strategies(self):
        result = assess_portfolio([])
        assert "无策略" in result.risk_warning

    def test_factor_exposure_in_output(self):
        result = assess_portfolio(_make_strategies())
        assert len(result.factor_exposure) > 0

    def test_recommendations_for_concentrated(self):
        # All growth strategies with identical factor sets
        strategies = [
            {"name": "g1", "expected_return": 15, "risk": 18, "max_drawdown": -15,
             "sharpe": 1.0, "factor_exposure": {"momentum_score": 0.8, "roc_10": 0.5}},
            {"name": "g2", "expected_return": 12, "risk": 16, "max_drawdown": -12,
             "sharpe": 0.8, "factor_exposure": {"momentum_score": 0.7, "roc_10": 0.4}},
        ]
        result = assess_portfolio(strategies)
        # Same factor set → low diversification
        assert result.diversification_score <= 0.3  # 1 - 2/2 = 0 (identical sets)
        assert result.risk_warning

    def test_to_dict(self):
        result = assess_portfolio(_make_strategies())
        d = result.to_dict()
        assert "allocation" in d
        assert "factor_exposure" in d
        assert "risk_warning" in d
        assert "diversification_score" in d
