"""
Volatility Factors — risk and dispersion measures.

Factors:
  - volatility: Historical volatility (low vol = high score)
  - bollinger_pos: Position within Bollinger Bands
  - bollinger_width: Bollinger Band width (squeeze/expansion)
  - atr_ratio: ATR relative to price
"""

import pandas as pd
import numpy as np

from src.factors.core.factor_base import BaseFactor


class VolatilityFactor(BaseFactor):
    """Historical volatility, inverted so low volatility = high score.

    Rationale: low-volatility environments are often healthier for trend following;
    high vol signals instability and regime change.
    """

    name = "volatility"
    category = "volatility"
    display_name = "Historical Volatility (20-day)"
    _description = "Annualized 20-day historical volatility, inverted. Low volatility → high score (favorable for trend following)."
    params = {"period": 20}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        returns = data["close"].pct_change()
        vol = returns.rolling(period).std() * np.sqrt(252)
        vol_norm = vol.rolling(252).rank(pct=True)
        return 1 - vol_norm  # Low vol → high score


class BollingerPositionFactor(BaseFactor):
    """Where price sits within the Bollinger Bands. 1 = upper band, 0 = lower band."""

    name = "bollinger_pos"
    category = "volatility"
    display_name = "Bollinger Band Position"
    _description = "Price position within Bollinger Bands (2σ). 1 = at upper band, 0 = at lower band, 0.5 = at midline."
    params = {"period": 20, "std_dev": 2.0}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        std_dev = self._params.get("std_dev", 2.0)

        ma = data["close"].rolling(period).mean()
        std = data["close"].rolling(period).std()
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        rng = (upper - lower).replace(0, np.nan)
        return ((data["close"] - lower) / rng).clip(0, 1)


class BollingerWidthFactor(BaseFactor):
    """Bollinger Band width — narrow = squeeze (potential breakout), wide = expansion."""

    name = "bollinger_width"
    category = "volatility"
    display_name = "Bollinger Band Width"
    _description = "Bollinger Band width relative to midline. Narrow bands signal compression (breakout imminent); wide bands signal expansion."
    params = {"period": 20, "std_dev": 2.0}
    output_range = (0.0, float("inf"))
    higher_is_better = False  # Context-dependent

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        std_dev = self._params.get("std_dev", 2.0)
        ma = data["close"].rolling(period).mean()
        std = data["close"].rolling(period).std()
        return (2 * std_dev * std) / ma.replace(0, np.nan)


class ATRRatioFactor(BaseFactor):
    """ATR as a fraction of price — measures relative volatility."""

    name = "atr_ratio"
    category = "volatility"
    display_name = "ATR / Price Ratio"
    _description = "Average True Range divided by close price. Measures relative volatility — higher = more volatile relative to price level."
    params = {"period": 14}
    output_range = (0.0, float("inf"))
    higher_is_better = False

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 14)
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        return atr / close.replace(0, np.nan)
