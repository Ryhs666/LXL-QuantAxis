"""
LXL QuantAxis — Factor Registry

Central factor catalog aggregating all factor types:

  Technical (18): momentum, trend, volatility, liquidity, pattern
  Fundamental (9): value, quality, growth
  Composite: multi-factor scoring

Usage:
    from src.factors.factor_registry import get_factor, list_factors

    # Get a factor and compute it
    factor = get_factor("momentum_score")
    signal = factor.calculate(data)

    # List all factors
    print(list_factors())

    # List by category
    print(list_factors("value"))
"""

from src.factors.core.registry import (
    registry,
    get_factor,
    list_factors,
    get_factor_names,
)

from src.factors.technical.momentum import (
    RSIFactor,
    ROCFactor,
    MomentumScoreFactor,
    PricePositionFactor,
    MACDHistFactor,
)
from src.factors.technical.trend import (
    MADeviationFactor,
    MAAlignmentFactor,
    MASlopeFactor,
    TrendStrengthFactor,
)
from src.factors.technical.volatility import (
    VolatilityFactor,
    BollingerPositionFactor,
    BollingerWidthFactor,
    ATRRatioFactor,
)
from src.factors.technical.liquidity import (
    VolumeRatioFactor,
    VolumeTrendFactor,
    OBVDivergenceFactor,
    HammerFactor,
    EngulfingFactor,
)
from src.factors.fundamental.value import PEFactor, PBFactor, EVEBITDAFactor
from src.factors.fundamental.quality import ROEFactor, GrossMarginFactor, FreeCashFlowFactor
from src.factors.fundamental.growth import RevenueGrowthFactor, EPSGrowthFactor, ProfitGrowthFactor


# ============================================================
# Auto-register all factor classes
# ============================================================

TECHNICAL_FACTORS = [
    # Momentum
    RSIFactor,
    ROCFactor,
    MomentumScoreFactor,
    PricePositionFactor,
    MACDHistFactor,
    # Trend
    MADeviationFactor,
    MAAlignmentFactor,
    MASlopeFactor,
    TrendStrengthFactor,
    # Volatility
    VolatilityFactor,
    BollingerPositionFactor,
    BollingerWidthFactor,
    ATRRatioFactor,
    # Liquidity & Pattern
    VolumeRatioFactor,
    VolumeTrendFactor,
    OBVDivergenceFactor,
    HammerFactor,
    EngulfingFactor,
]

FUNDAMENTAL_FACTORS = [
    # Value
    PEFactor,
    PBFactor,
    EVEBITDAFactor,
    # Quality
    ROEFactor,
    GrossMarginFactor,
    FreeCashFlowFactor,
    # Growth
    RevenueGrowthFactor,
    EPSGrowthFactor,
    ProfitGrowthFactor,
]

ALL_FACTOR_CLASSES = TECHNICAL_FACTORS + FUNDAMENTAL_FACTORS


def _auto_register():
    """Register all factor classes into the global registry."""
    for factor_cls in ALL_FACTOR_CLASSES:
        try:
            instance = factor_cls()
            if instance.name not in registry:
                registry.register(instance)
        except Exception:
            pass

    # Also seed legacy factors from definitions.py
    registry.initialize_from_legacy()


# Run on import
_auto_register()


# ============================================================
# Public API
# ============================================================

__all__ = [
    "registry",
    "get_factor",
    "list_factors",
    "get_factor_names",
    "TECHNICAL_FACTORS",
    "FUNDAMENTAL_FACTORS",
    "ALL_FACTOR_CLASSES",
]
