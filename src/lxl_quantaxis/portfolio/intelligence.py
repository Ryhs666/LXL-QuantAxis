"""Portfolio Intelligence — multi-strategy management and risk analysis.

Manages multiple StrategySpec instances with factor exposure tracking,
risk assessment, and allocation.  Connects to existing portfolio modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.lxl_quantaxis.core.logging import get_logger

_log = get_logger("portfolio.intelligence")


# ═══════════════════════════════════════════════════════════
# Data models
# ═══════════════════════════════════════════════════════════

@dataclass
class StrategyProfile:
    name: str = ""
    expected_return: float = 0.0   # annualized %
    risk: float = 0.0              # annualized volatility %
    max_drawdown: float = 0.0      # %
    sharpe: float = 0.0
    factor_exposure: dict[str, float] = field(default_factory=dict)
    allocation: float = 0.0        # portfolio weight


@dataclass
class PortfolioAssessment:
    allocation: list[dict] = field(default_factory=list)
    factor_exposure: dict[str, float] = field(default_factory=dict)
    risk_warning: str = ""
    recommendations: list[str] = field(default_factory=list)
    expected_return: float = 0.0
    expected_risk: float = 0.0
    diversification_score: float = 0.0
    source: str = "rule"

    def to_dict(self) -> dict:
        return {
            "allocation": self.allocation,
            "factor_exposure": self.factor_exposure,
            "risk_warning": self.risk_warning,
            "recommendations": self.recommendations,
            "expected_return": self.expected_return,
            "expected_risk": self.expected_risk,
            "diversification_score": self.diversification_score,
            "source": self.source,
        }


# ═══════════════════════════════════════════════════════════
# Factor exposure analysis
# ═══════════════════════════════════════════════════════════

_FACTOR_CATEGORIES = {
    "growth":   ["momentum_score", "roc_10", "trend_strength"],
    "momentum": ["momentum_score", "rsi_norm", "roc_10"],
    "value":    ["ma_deviation", "bollinger_pos", "volatility"],
    "volatility": ["volatility", "atr_ratio", "bollinger_width"],
    "volume":   ["volume_ratio", "volume_trend", "obv_divergence"],
    "trend":    ["ma_slope", "ma_alignment", "trend_strength"],
}


def _compute_factor_exposure(profiles: list[StrategyProfile]) -> dict[str, float]:
    """Aggregate factor exposure across all strategies weighted by allocation."""
    exposure: dict[str, float] = {}
    total_weight = sum(p.allocation for p in profiles)
    if total_weight == 0:
        return exposure

    for profile in profiles:
        w = profile.allocation / total_weight
        for factor, value in profile.factor_exposure.items():
            exposure[factor] = exposure.get(factor, 0.0) + w * value

    return exposure


def _analyze_factor_concentration(exposure: dict[str, float]) -> dict[str, float]:
    """Aggregate per-factor exposure into category-level concentrations."""
    result: dict[str, float] = {}
    for category, factors in _FACTOR_CATEGORIES.items():
        cat_value = sum(exposure.get(f, 0.0) for f in factors)
        count = sum(1 for f in factors if f in exposure)
        result[category] = round(cat_value / max(count, 1), 4)
    return result


# ═══════════════════════════════════════════════════════════
# Risk analysis
# ═══════════════════════════════════════════════════════════

def _compute_correlation_warning(profiles: list[StrategyProfile]) -> str:
    """Check if strategies are too similar (all same factor exposure)."""
    if len(profiles) < 2:
        return "单一策略, 无分散化。"
    # Simple heuristic: if all strategies are growth-heavy
    growth_count = sum(
        1 for p in profiles
        if p.factor_exposure.get("momentum_score", 0) > 0.3
    )
    if growth_count >= len(profiles) * 0.75:
        return "策略高度集中于成长因子, 当市场风格切换时组合可能同步回撤。考虑加入价值或低波动策略。"
    return "因子暴露有一定分散度, 相关性适中。"


def _compute_concentration_warning(profiles: list[StrategyProfile]) -> str:
    """Check for over-concentration in a single strategy."""
    if not profiles:
        return ""
    max_alloc = max(p.allocation for p in profiles)
    if max_alloc > 0.50:
        return f"单一策略权重{max_alloc:.0%}过高, 建议分散到多策略。"
    return "策略权重分配合理。"


def _compute_diversification_score(profiles: list[StrategyProfile]) -> float:
    """Simple diversification score: 0 (all same) to 1 (fully diverse)."""
    if len(profiles) < 2:
        return 0.0
    exposures = [set(p.factor_exposure.keys()) for p in profiles]
    # Jaccard diversity
    union = set.union(*exposures) if exposures else set()
    intersection = set.intersection(*exposures) if len(exposures) > 1 else set()
    if not union:
        return 0.5
    return round(1.0 - len(intersection) / len(union), 2)


# ═══════════════════════════════════════════════════════════
# Allocation methods
# ═══════════════════════════════════════════════════════════

def _allocate_equal(profiles: list[StrategyProfile]) -> list[StrategyProfile]:
    n = len(profiles)
    for p in profiles:
        p.allocation = round(1.0 / n, 4)
    return profiles


def _allocate_risk_weighted(profiles: list[StrategyProfile]) -> list[StrategyProfile]:
    """Allocate inversely proportional to risk (lower risk = higher weight)."""
    risks = np.array([max(p.risk, 0.01) for p in profiles])
    inv_risks = 1.0 / risks
    weights = inv_risks / inv_risks.sum()
    for p, w in zip(profiles, weights):
        p.allocation = round(float(w), 4)
    return profiles


def _allocate_sharpe_weighted(profiles: list[StrategyProfile]) -> list[StrategyProfile]:
    """Allocate proportional to Sharpe (minimum 0 weight)."""
    sharpes = np.array([max(p.sharpe, 0.0) for p in profiles])
    total = sharpes.sum()
    if total == 0:
        return _allocate_equal(profiles)
    weights = sharpes / total
    for p, w in zip(profiles, weights):
        p.allocation = round(float(w), 4)
    return profiles


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def assess_portfolio(
    strategies: list[dict],
    method: str = "risk_weighted",
) -> PortfolioAssessment:
    """Analyze a portfolio of strategies and produce allocation + risk assessment.

    Args:
        strategies: List of {
            name, expected_return, risk, max_drawdown, sharpe, factor_exposure
        }
        method: allocation method (equal, risk_weighted, sharpe_weighted)

    Returns:
        PortfolioAssessment with allocation, exposure, risk, recommendations
    """
    profiles = [
        StrategyProfile(
            name=s.get("name", f"strategy_{i}"),
            expected_return=float(s.get("expected_return", 0)),
            risk=float(s.get("risk", 5.0)),
            max_drawdown=float(s.get("max_drawdown", 0)),
            sharpe=float(s.get("sharpe", 0)),
            factor_exposure={
                str(k): float(v)
                for k, v in s.get("factor_exposure", {}).items()
            },
        )
        for i, s in enumerate(strategies)
    ]

    if not profiles:
        return PortfolioAssessment(
            risk_warning="无策略", source="rule",
        )

    # Allocate
    allocators = {
        "equal": _allocate_equal,
        "risk_weighted": _allocate_risk_weighted,
        "sharpe_weighted": _allocate_sharpe_weighted,
    }
    alloc_fn = allocators.get(method, _allocate_equal)
    profiles = alloc_fn(profiles)

    # Factor exposure
    raw_exposure = _compute_factor_exposure(profiles)
    category_exposure = _analyze_factor_concentration(raw_exposure)

    # Risk
    corr_warning = _compute_correlation_warning(profiles)
    conc_warning = _compute_concentration_warning(profiles)
    div_score = _compute_diversification_score(profiles)

    # Build recommendations
    recommendations = []
    if div_score < 0.3:
        recommendations.append("策略同质化严重, 建议引入不同因子类别的策略")
    if category_exposure.get("growth", 0) > 0.6:
        recommendations.append("成长因子暴露过高, 考虑增加价值或低波动策略")
    if any(p.max_drawdown < -20 for p in profiles):
        recommendations.append("存在高回撤策略, 建议降低其权重或添加止损")

    # Expected portfolio return/risk (simple weighted average)
    exp_ret = round(sum(p.allocation * p.expected_return for p in profiles), 2)
    exp_risk = round(
        np.sqrt(sum((p.allocation * p.risk / 100) ** 2 for p in profiles)) * 100, 2
    ) if profiles else 0.0

    # Combine risk warnings
    risk_warning = f"{corr_warning} {conc_warning}".strip()

    return PortfolioAssessment(
        allocation=[{
            "name": p.name, "weight": p.allocation,
            "expected_return": p.expected_return, "risk": p.risk,
        } for p in profiles],
        factor_exposure=category_exposure,
        risk_warning=risk_warning,
        recommendations=recommendations,
        expected_return=exp_ret,
        expected_risk=exp_risk,
        diversification_score=div_score,
        source="rule",
    )
