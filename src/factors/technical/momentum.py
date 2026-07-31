"""
Momentum Factors — price and return-based momentum signals.

Factors:
  - rsi_norm: Normalized RSI (0=oversold, 1=overbought)
  - roc_10: 10-day rate of change
  - momentum_score: Multi-period momentum composite
  - price_position: Position within N-day high-low range
  - macd_hist: MACD histogram (momentum strength)
"""

import pandas as pd
import numpy as np

from src.factors.core.factor_base import BaseFactor


class RSIFactor(BaseFactor):
    """Normalized RSI: measures speed and change of price movements.

    Output: 0–1 where 0 = deeply oversold, 1 = deeply overbought.
    Reversal traders buy near 0, trend traders buy near 0.7+ pullbacks.
    """

    name = "rsi_norm"
    category = "momentum"
    display_name = "RSI (Normalized)"
    _description = "Relative Strength Index normalized to 0–1. Measures price velocity and identifies overbought/oversold extremes."
    params = {"period": 14}
    higher_is_better = False  # Context-dependent; low=oversold (potential buy)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 14)
        delta = data["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi / 100.0


class ROCFactor(BaseFactor):
    """Rate of Change: pure price momentum over a fixed lookback."""

    name = "roc_10"
    category = "momentum"
    display_name = "Rate of Change (10-day)"
    _description = "10-day price rate of change, sigmoid-normalized to 0–1. Captures directional momentum."
    params = {"period": 10}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 10)
        roc = (data["close"] / data["close"].shift(period) - 1) * 100
        return self._sigmoid(roc, center=0.0, steepness=0.5)


class MomentumScoreFactor(BaseFactor):
    """Multi-period momentum: fraction of lookback windows with positive return."""

    name = "momentum_score"
    category = "momentum"
    display_name = "Momentum Score (Multi-Period)"
    _description = "Multi-period momentum composite: fraction of [5, 10, 20, 60] day windows with positive returns."
    params = {"periods": [5, 10, 20, 60]}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        periods = self._params.get("periods", [5, 10, 20, 60])
        scores = []
        for p in periods:
            ret = data["close"].pct_change(p)
            scores.append((ret > 0).astype(float))
        return pd.concat(scores, axis=1).mean(axis=1)


class PricePositionFactor(BaseFactor):
    """Where current price sits within its N-period range."""

    name = "price_position"
    category = "momentum"
    display_name = "Price Position (60-day)"
    _description = "Current price position within the 60-day high-low range. 1 = at highs, 0 = at lows."
    params = {"period": 60}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 60)
        h = data["high"].rolling(period).max()
        l = data["low"].rolling(period).min()
        rng = (h - l).replace(0, np.nan)
        pos = (data["close"] - l) / rng
        return pos.clip(0, 1)


class MACDHistFactor(BaseFactor):
    """MACD histogram: difference between fast/slow EMAs, signal-line adjusted."""

    name = "macd_hist"
    category = "momentum"
    display_name = "MACD Histogram"
    _description = "MACD histogram normalized via sigmoid. Positive = bullish momentum, negative = bearish."
    params = {"fast": 12, "slow": 26, "signal": 9}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        fast = self._params.get("fast", 12)
        slow = self._params.get("slow", 26)
        signal = self._params.get("signal", 9)

        ema_f = data["close"].ewm(span=fast, adjust=False).mean()
        ema_s = data["close"].ewm(span=slow, adjust=False).mean()
        dif = ema_f - ema_s
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2 * (dif - dea)

        # Scale by average price
        avg_price = data["close"].rolling(100).mean()
        scale = hist * 10 / avg_price.replace(0, np.nan)
        return self._sigmoid(scale, center=0.0, steepness=1.0)
