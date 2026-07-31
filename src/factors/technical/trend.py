"""
Trend Factors — directional bias and trend quality signals.

Factors:
  - ma_deviation: Price deviation from moving average
  - ma_alignment: Multi-timeframe MA alignment (bullish/bearish)
  - ma_slope: Moving average slope (trend direction)
  - trend_strength: ADX-like trend strength indicator
"""

import pandas as pd
import numpy as np

from src.factors.core.factor_base import BaseFactor


class MADeviationFactor(BaseFactor):
    """Distance of price from its moving average, sigmoid-normalized."""

    name = "ma_deviation"
    category = "trend"
    display_name = "MA Deviation (20-day)"
    _description = "Price deviation from 20-day SMA, sigmoid-normalized. > 0.5 = above MA (bullish), < 0.5 = below MA (bearish)."
    params = {"period": 20}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        ma = data["close"].rolling(period).mean()
        pct = (data["close"] - ma) / ma.replace(0, np.nan) * 100
        return self._sigmoid(pct, center=0.0, steepness=0.5)


class MAAlignmentFactor(BaseFactor):
    """Multi-timeframe moving average alignment.

    1.0 = fully bullish (short > mid > long)
    0.0 = fully bearish (short < mid < long)
    0.5 = mixed / neutral
    """

    name = "ma_alignment"
    category = "trend"
    display_name = "MA Alignment (5/20/60)"
    _description = "Multi-timeframe moving average alignment. 1 = fully bullish (short>mid>long), 0 = fully bearish."
    params = {"short": 5, "mid": 20, "long": 60}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        short_p = self._params.get("short", 5)
        mid_p = self._params.get("mid", 20)
        long_p = self._params.get("long", 60)

        ma_s = data["close"].rolling(short_p).mean()
        ma_m = data["close"].rolling(mid_p).mean()
        ma_l = data["close"].rolling(long_p).mean()

        bullish = (ma_s > ma_m) & (ma_m > ma_l)
        bearish = (ma_s < ma_m) & (ma_m < ma_l)

        score = bullish.astype(float) * 1.0
        score += (~bullish & ~bearish).astype(float) * 0.5
        return score


class MASlopeFactor(BaseFactor):
    """Slope of the moving average — steepness of trend."""

    name = "ma_slope"
    category = "trend"
    display_name = "MA Slope (20-day)"
    _description = "20-day moving average slope, sigmoid-normalized. Positive slope = uptrend, higher value = steeper trend."
    params = {"period": 20, "lookback": 5}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 20)
        lookback = self._params.get("lookback", 5)
        ma = data["close"].rolling(period).mean()
        slope = (ma - ma.shift(lookback)) / ma.shift(lookback).replace(0, np.nan) * 100
        return self._sigmoid(slope, center=0.0, steepness=5.0)


class TrendStrengthFactor(BaseFactor):
    """ADX-like trend strength indicator. 1 = strong trend, 0 = sideways."""

    name = "trend_strength"
    category = "trend"
    display_name = "Trend Strength (ADX-like)"
    _description = "ADX-like trend strength indicator. 1 = strong directional trend, 0 = range-bound / sideways."
    params = {"period": 14}

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        period = self._params.get("period", 14)
        high, low, close = data["high"], data["low"], data["close"]

        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)

        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0), index=data.index)
        minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0), index=data.index)

        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)

        dx = abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan) * 100
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()
        return (adx / 100.0).clip(0, 1)
