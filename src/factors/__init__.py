"""
LXL QuantAxis v6.0 — Factor Research Laboratory

Institutional-grade multi-factor research framework.

Structure:
  core/         — BaseFactor, FactorRegistry, FactorEvaluator
  technical/    — 18 technical factors (momentum, trend, volatility, liquidity, pattern)
  fundamental/  — 9 institutional fundamental factors (value, quality, growth)
  composite/    — Multi-factor scoring and composition

Legacy compatibility:
  definitions.py   — FactorCalculator + FACTOR_REGISTRY (unchanged)
  fundamental.py   — FundamentalFactors class (unchanged)
  composer.py      — SignalComposer + PRESET_STRATEGIES (unchanged)
"""

# --- Legacy exports (backward compatible) ---
from src.factors.definitions import (
    Factor,
    FactorCalculator,
    FACTOR_REGISTRY,
)
from src.factors.fundamental import FundamentalFactors, fundamental
from src.factors.composer import (
    Condition,
    SignalRule,
    SignalComposer,
    PRESET_STRATEGIES,
    create_contrarian_v1,
    create_trend_following_v1,
    create_volume_breakout_v1,
    create_mean_reversion_v2,
)

# --- New framework exports ---
from src.factors.core.factor_base import BaseFactor, FactorMetadata
from src.factors.core.registry import (
    FactorRegistry,
    registry,
    get_factor,
    list_factors,
    get_factor_names,
)
from src.factors.core.evaluator import (
    FactorEvaluator,
    evaluate_factor,
    evaluate_all_factors,
)
from src.factors.composite.scoring import FactorScoring, composite_score

# --- Auto-register all factor classes ---
from src.factors.factor_registry import (
    TECHNICAL_FACTORS,
    FUNDAMENTAL_FACTORS,
    ALL_FACTOR_CLASSES,
)

__all__ = [
    # Legacy
    "Factor",
    "FactorCalculator",
    "FACTOR_REGISTRY",
    "FundamentalFactors",
    "fundamental",
    "Condition",
    "SignalRule",
    "SignalComposer",
    "PRESET_STRATEGIES",
    "create_contrarian_v1",
    "create_trend_following_v1",
    "create_volume_breakout_v1",
    "create_mean_reversion_v2",
    # New framework
    "BaseFactor",
    "FactorMetadata",
    "FactorRegistry",
    "registry",
    "get_factor",
    "list_factors",
    "get_factor_names",
    "FactorEvaluator",
    "evaluate_factor",
    "evaluate_all_factors",
    "FactorScoring",
    "composite_score",
    # Factor classes
    "TECHNICAL_FACTORS",
    "FUNDAMENTAL_FACTORS",
    "ALL_FACTOR_CLASSES",
]
