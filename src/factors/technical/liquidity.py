"""
Liquidity & Pattern Factors — volume-based and candlestick pattern signals.

Factors:
  - volume_ratio: Short/long-term volume ratio (volume surge detection)
  - volume_trend: Price-volume coordination health
  - obv_divergence: OBV-price divergence detection
  - hammer: Hammer candlestick pattern (bullish reversal)
  - engulfing: Engulfing candlestick pattern (bullish reversal)
"""

import pandas as pd
import numpy as np

from src.factors.core.factor_base import BaseFactor


class VolumeRatioFactor(BaseFactor):
    """Short-term vs long-term average volume. > 0.5 = above-average volume."""

    name = "volume_ratio"
    category = "liquidity"
    display_name = "Volume Ratio (5/20)"
    _description = "Ratio of 5-day to 20-day average volume, sigmoid-normalized. Detects volume surges relative to baseline."
    params = {"short": 5, "long": 20}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        short_p = self._params.get("short", 5)
        long_p = self._params.get("long", 20)

        vol_short = data["volume"].rolling(short_p).mean()
        vol_long = data["volume"].rolling(long_p).mean()
        ratio = (vol_short / vol_long.replace(0, np.nan)).fillna(1.0)
        return self._sigmoid(ratio, center=1.0, steepness=3.0)


class VolumeTrendFactor(BaseFactor):
    """Price-volume coordination health. 1 = healthy (price↑ & volume↑), 0 = divergence."""

    name = "volume_trend"
    category = "liquidity"
    display_name = "Volume Trend (Price-Volume Health)"
    _description = "Price-volume coordination health over a rolling window. High score = price and volume moving together (confirmation)."
    params = {"period": 10}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 10)
        price_up = (data["close"].diff() > 0)
        vol_up = (data["volume"].diff() > 0)
        healthy = (price_up & vol_up) | (~price_up & ~vol_up)
        healthy = healthy.astype(float)
        return healthy.rolling(period).mean()


class OBVDivergenceFactor(BaseFactor):
    """OBV vs price divergence. High = OBV confirms price; low = bearish divergence."""

    name = "obv_divergence"
    category = "liquidity"
    display_name = "OBV Divergence"
    _description = "On-Balance Volume divergence from price. High score = OBV confirms price trend; low score = OBV diverges (warning)."
    params = {"period": 20}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        obv = (data["volume"] * np.sign(data["close"].diff())).cumsum()
        price_ret = data["close"].pct_change(period)
        obv_ret = obv.pct_change(period)
        same_dir = ((price_ret > 0) & (obv_ret > 0)) | ((price_ret < 0) & (obv_ret < 0))
        return same_dir.rolling(period).mean()


class HammerFactor(BaseFactor):
    """Hammer candlestick pattern — bullish reversal signal after a downtrend."""

    name = "hammer"
    category = "pattern"
    display_name = "Hammer Pattern"
    _description = "Hammer candlestick detection. Identifies candles with long lower wicks and small bodies — potential bullish reversal."
    params = {"lookback": 2}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        lookback = self._params.get("lookback", 2)
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = abs(c - o)
        total_range = h - l
        lower_wick = np.where(c > o, o - l, c - l)

        body_ratio = (body / total_range.replace(0, np.nan)).fillna(1)
        wick_ratio = (lower_wick / body.replace(0, np.nan)).fillna(0)

        hammer = (wick_ratio > 2) & (body_ratio < 0.3)
        return hammer.rolling(lookback).max().astype(float)


class EngulfingFactor(BaseFactor):
    """Bullish engulfing pattern — strong reversal signal."""

    name = "engulfing"
    category = "pattern"
    display_name = "Engulfing Pattern"
    _description = "Bullish engulfing candlestick pattern detection. Today's green body engulfs yesterday's red body — strong reversal signal."
    params = {}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        o, c = data["open"], data["close"]
        prev_o, prev_c = o.shift(1), c.shift(1)

        prev_red = prev_c < prev_o
        today_green = c > o
        body_bigger = abs(c - o) > abs(prev_c - prev_o)
        engulf = (c > prev_o) & (o < prev_c)

        return (prev_red & today_green & body_bigger & engulf).rolling(3).max().astype(float)
