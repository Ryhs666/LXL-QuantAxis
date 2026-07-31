"""
Factor Base Framework — institutional-grade factor abstraction.

Every factor in LXL QuantAxis inherits from BaseFactor.
This ensures consistency across technical, fundamental, and composite factors.

Design principles:
  - Each factor has a name, category, and description
  - calculate() returns a standardized pd.Series (0–1 range where applicable)
  - Metadata is self-describing for registry and documentation
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class FactorMetadata:
    """Rich metadata for a single factor."""

    name: str                                    # Unique factor identifier
    category: str                                # momentum / trend / volatility / liquidity /
                                                  #   pattern / value / quality / growth / composite
    display_name: str = ""                       # Human-readable name
    description: str = ""                        # One-paragraph explanation
    input_columns: List[str] = field(default_factory=list)  # Required OHLCV columns
    output_range: tuple = (0.0, 1.0)             # Typical output range
    params: Dict[str, Any] = field(default_factory=dict)   # Default parameters
    source: str = "computed"                     # computed / fundamental / alternative
    unit: str = ""                               # %, ratio, score, etc.
    higher_is_better: bool = True                # Direction for signal interpretation
    references: List[str] = field(default_factory=list)    # Academic or industry references

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
            "input_columns": self.input_columns,
            "output_range": list(self.output_range),
            "params": self.params,
            "source": self.source,
            "unit": self.unit,
            "higher_is_better": self.higher_is_better,
            "references": self.references,
        }


class BaseFactor:
    """
    Abstract base class for all factors in the LXL QuantAxis framework.

    Subclasses must implement:
      - calculate(data) → pd.Series

    Subclasses may override:
      - metadata (FactorMetadata)
      - description() → str
    """

    # --- Subclass-level defaults (override in subclasses) ---
    name: str = None
    category: str = None
    display_name: str = ""
    _description: str = ""
    input_columns: List[str] = ["open", "high", "low", "close", "volume"]
    params: Dict[str, Any] = {}
    output_range: tuple = (0.0, 1.0)
    source: str = "computed"
    higher_is_better: bool = True

    def __init__(self, **kwargs):
        """Override default params with kwargs."""
        self._params = {**self.__class__.params, **kwargs}
        self._cached_metadata: Optional[FactorMetadata] = None

    # ---- Metadata ----

    @property
    def metadata(self) -> FactorMetadata:
        """Lazily-built factor metadata."""
        if self._cached_metadata is None:
            self._cached_metadata = FactorMetadata(
                name=self.name or self.__class__.__name__,
                category=self.category or "unknown",
                display_name=self.display_name or self.name or "",
                description=self._description or self.__doc__ or "",
                input_columns=self.input_columns,
                output_range=self.output_range,
                params=self._params,
                source=self.source,
                higher_is_better=self.higher_is_better,
            )
        return self._cached_metadata

    def description(self) -> str:
        """Return a human-readable description of this factor."""
        return self.metadata.description

    def to_dict(self) -> dict:
        """Serialize factor metadata to dict."""
        return self.metadata.to_dict()

    # ---- Core computation ----

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute factor values for the given OHLCV DataFrame.

        Args:
            data: DataFrame with columns [open, high, low, close, volume] and date index.

        Returns:
            pd.Series of factor values, aligned to data.index.
            Values should be normalized to the factor's output_range where applicable.
        """
        raise NotImplementedError(
            f"Factor '{self.name}' must implement calculate(data) → pd.Series"
        )

    # ---- Helpers ----

    @staticmethod
    def _sigmoid(x: pd.Series, center: float = 0.0, steepness: float = 1.0) -> pd.Series:
        """Map values to (0, 1) via sigmoid. Center controls the inflection point."""
        return 1.0 / (1.0 + np.exp(-steepness * (x - center)))

    @staticmethod
    def _minmax(x: pd.Series, period: int = 252) -> pd.Series:
        """Rolling min-max normalization to (0, 1)."""
        lo = x.rolling(period).min()
        hi = x.rolling(period).max()
        rng = (hi - lo).replace(0, np.nan)
        return ((x - lo) / rng).clip(0, 1)

    @staticmethod
    def _rank_pct(x: pd.Series, period: int = 252) -> pd.Series:
        """Rolling percentile rank (0–1)."""
        return x.rolling(period).rank(pct=True)

    @staticmethod
    def _zscore(x: pd.Series, period: int = 252) -> pd.Series:
        """Rolling z-score."""
        mu = x.rolling(period).mean()
        sigma = x.rolling(period).std().replace(0, np.nan)
        return (x - mu) / sigma

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}' category='{self.category}'>"
