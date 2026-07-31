"""
Factor Registry — central catalog of all registered factors.

Provides:
  - Automatic factor registration via decorator or direct call
  - Lookup: get_factor(name), list_factors(), list_by_category()
  - Integration with the legacy FACTOR_REGISTRY from definitions.py

All factors in the system, whether defined as BaseFactor subclasses or
legacy Factor dataclass entries, are accessible through this registry.
"""

from typing import Dict, List, Optional, Union, Type
import pandas as pd

from src.factors.core.factor_base import BaseFactor, FactorMetadata


class FactorRegistry:
    """
    Singleton registry for all factors in LXL QuantAxis.

    Usage:
        registry = FactorRegistry()

        # Register a factor instance
        registry.register(MomentumFactor())

        # Look up
        factor = registry.get("momentum_20")
        signal = factor.calculate(data)

        # List all
        for name, meta in registry.list_all().items():
            print(name, meta.category)
    """

    _instance: Optional["FactorRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factors: Dict[str, BaseFactor] = {}
            cls._instance._metadata: Dict[str, FactorMetadata] = {}
            cls._instance._initialized = False
        return cls._instance

    # ---- Registration ----

    def register(self, factor: BaseFactor) -> BaseFactor:
        """
        Register a factor instance.

        Args:
            factor: A BaseFactor subclass instance.

        Returns:
            The registered factor (for decorator use).
        """
        name = factor.name
        if not name:
            raise ValueError(f"Factor {factor} has no name — cannot register")
        self._factors[name] = factor
        self._metadata[name] = factor.metadata
        return factor

    def register_class(self, factor_cls: Type[BaseFactor], **kwargs):
        """
        Register a factor by class. Instantiates with kwargs.

        Usage:
            registry.register_class(MomentumFactor, period=20)
        """
        instance = factor_cls(**kwargs)
        return self.register(instance)

    def register_legacy(self, name: str, category: str, description: str,
                        compute_fn, params: dict = None):
        """
        Register a factor from legacy FactorCalculator method.

        This bridges the existing FACTOR_REGISTRY (definitions.py) into
        the new BaseFactor system without changing the old code.
        """
        from src.factors.core.factor_base import BaseFactor

        params = params or {}

        class LegacyFactor(BaseFactor):
            pass

        factor = LegacyFactor()
        factor.name = name
        factor.category = category
        factor._description = description
        factor._params = params
        factor.input_columns = ["open", "high", "low", "close", "volume"]
        factor.source = "computed"

        # Wrap the compute function
        def _calculate(self, data):
            from src.factors.definitions import FactorCalculator
            calc = FactorCalculator(data)
            method_name = f"f_{name}" if hasattr(calc, f"f_{name}") else None

            if method_name is None:
                # Try to find the method by mapping
                method_map = {
                    "rsi_norm": "f_rsi",
                    "roc_10": "f_roc",
                    "price_position": "f_price_position",
                    "momentum_score": "f_momentum_score",
                    "macd_hist": "f_macd_hist",
                    "ma_deviation": "f_ma_deviation",
                    "ma_alignment": "f_ma_alignment",
                    "ma_slope": "f_ma_slope",
                    "trend_strength": "f_adx_like",
                    "volatility": "f_volatility",
                    "bollinger_pos": "f_bollinger_position",
                    "bollinger_width": "f_bollinger_width",
                    "atr_ratio": "f_atr_ratio",
                    "volume_ratio": "f_volume_ratio",
                    "volume_trend": "f_volume_trend",
                    "obv_divergence": "f_obv_divergence",
                    "hammer": "f_hammer",
                    "engulfing": "f_engulfing",
                }
                method_name = method_map.get(name)

            if method_name and hasattr(calc, method_name):
                return getattr(calc, method_name)(**params)
            elif compute_fn:
                return compute_fn(data, **params)
            else:
                raise ValueError(f"Unknown legacy factor: {name}")

        factor.calculate = _calculate.__get__(factor, LegacyFactor)
        return self.register(factor)

    def register_many(self, factors: List[BaseFactor]) -> List[BaseFactor]:
        """Register multiple factor instances at once."""
        return [self.register(f) for f in factors]

    # ---- Lookup ----

    def get(self, name: str) -> Optional[BaseFactor]:
        """Retrieve a factor by name. Returns None if not found."""
        return self._factors.get(name)

    def get_metadata(self, name: str) -> Optional[FactorMetadata]:
        """Retrieve factor metadata by name."""
        return self._metadata.get(name)

    def list_all(self) -> Dict[str, FactorMetadata]:
        """Return {name: FactorMetadata} for all registered factors."""
        return dict(self._metadata)

    def list_factors(self) -> List[str]:
        """Return list of all registered factor names."""
        return sorted(self._factors.keys())

    def list_by_category(self, category: str) -> List[str]:
        """Return factor names filtered by category."""
        return sorted([
            name for name, meta in self._metadata.items()
            if meta.category == category
        ])

    def categories(self) -> List[str]:
        """Return list of unique factor categories."""
        return sorted(set(m.category for m in self._metadata.values()))

    def summary(self) -> pd.DataFrame:
        """Return a DataFrame summary of all registered factors."""
        rows = []
        for name, meta in self._metadata.items():
            rows.append({
                "name": name,
                "category": meta.category,
                "display_name": meta.display_name,
                "description": meta.description,
                "source": meta.source,
                "higher_is_better": meta.higher_is_better,
            })
        return pd.DataFrame(rows)

    # ---- Initialization ----

    def initialize_from_legacy(self):
        """
        Seed the registry with all factors from the legacy FACTOR_REGISTRY
        in definitions.py. Called once on first import.
        """
        if self._initialized:
            return

        try:
            from src.factors.definitions import FACTOR_REGISTRY as LEGACY

            for name, factor in LEGACY.items():
                self.register_legacy(
                    name=name,
                    category=factor.category,
                    description=factor.description,
                    params=factor.params,
                    compute_fn=None,
                )
        except ImportError:
            pass

        self._initialized = True

    def __len__(self):
        return len(self._factors)

    def __contains__(self, name: str) -> bool:
        return name in self._factors

    def __iter__(self):
        return iter(self._factors)


# --- Global singleton ---

registry = FactorRegistry()


# --- Convenience functions ---

def get_factor(name: str) -> Optional[BaseFactor]:
    """Get a registered factor by name."""
    return registry.get(name)


def list_factors(category: str = None) -> List[str]:
    """List registered factors, optionally filtered by category."""
    if category:
        return registry.list_by_category(category)
    return registry.list_factors()


def get_factor_names() -> List[str]:
    """Alias for list_factors()."""
    return registry.list_factors()
