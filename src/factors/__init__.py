"""因子库模块 — 28 因子 + AI 因子挖掘"""

from .definitions import Factor, FactorCalculator, FACTOR_REGISTRY
from .composer import SignalComposer, Condition, PRESET_STRATEGIES

# v2.0: AI 因子挖掘 (遗传编程)
try:
    from src.ai.factor_discovery import (
        GeneticFactorMiner,
        FactorValidator as GPFactorValidator,
        run_discover_cli,
    )
    _HAS_FACTOR_DISCOVERY = True
except ImportError:
    _HAS_FACTOR_DISCOVERY = False
