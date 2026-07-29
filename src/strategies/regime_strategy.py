"""
市场状态感知策略 (v4.7)
解决震荡市频繁假信号的核心问题

状态判定:
  STRONG_BULL  → 重仓做多 (ADX>20, MA多头, 价格>20MA)
  WEAK_BULL    → 轻仓做多
  RANGING      → 观望不动
  WEAK_BEAR    → 轻仓做空
  STRONG_BEAR  → 重仓做空 (ADX>20, MA空头, 价格<20MA)

信号生成:
  BULL状态 → 回调买入 + RSI确认
  BEAR状态 → 反弹做空 + RSI确认
  RANGING  → 不交易
"""

from typing import Optional
import pandas as pd
import numpy as np
from src.models.strategy import Signal, StrategyConfig
from src.strategies.library import BaseStrategy


class RegimeAwareStrategy(BaseStrategy):
    """市场状态感知双向策略"""

    def __init__(self, config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self._regime = "RANGING"
        self._regime_history = []

    def _detect_regime(self, data: pd.DataFrame) -> str:
        """5状态分类"""
        if len(data) < 120:
            return "RANGING"

        close = data["close"]
        ma20 = self.sma(data, 20)
        ma60 = self.sma(data, 60)
        adx = self._calc_adx(data, 14)
        ma_slope = (ma20.iloc[-1] / ma20.iloc[-10] - 1) if len(ma20) >= 10 else 0

        # 趋势方向
        bull_alignment = (ma20.iloc[-1] > ma60.iloc[-1] and close.iloc[-1] > ma20.iloc[-1])
        bear_alignment = (ma20.iloc[-1] < ma60.iloc[-1] and close.iloc[-1] < ma20.iloc[-1])

        # 趋势强度
        strong_trend = adx > 22
        weak_trend = adx > 15

        # 波动判断 (低波动=震荡)
        bb = self.bollinger(data, 20, 2.0)
        bb_width = (bb["upper"].iloc[-1] - bb["lower"].iloc[-1]) / bb["middle"].iloc[-1]
        is_ranging = bb_width < 0.04 and adx < 15

        if is_ranging:
            return "RANGING"
        elif bull_alignment and strong_trend and ma_slope > 0.003:
            return "STRONG_BULL"
        elif bull_alignment and weak_trend:
            return "WEAK_BULL"
        elif bear_alignment and strong_trend and ma_slope < -0.003:
            return "STRONG_BEAR"
        elif bear_alignment and weak_trend:
            return "WEAK_BEAR"
        else:
            return self._regime  # 保持上次状态

    def _calc_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()

        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = pd.Series(0.0, index=data.index)
        minus_dm = pd.Series(0.0, index=data.index)
        plus_dm[(up > down) & (up > 0)] = up
        minus_dm[(down > up) & (down > 0)] = down

        plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, 1))
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, 1))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()
        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 15.0

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < 120:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]

        has_long = symbol in portfolio.positions
        has_short = ("SHORT_" + symbol) in portfolio.positions

        self._regime = self._detect_regime(data)
        self._regime_history.append(self._regime)

        rsi_val = self.rsi(data, 14).iloc[-1]
        bb = self.bollinger(data, 20, 2.0)

        # === 开仓逻辑 ===
        if not has_long and not has_short:
            if "BULL" in self._regime:
                # 等回调到布林下轨+RSI低位
                near_low = current_price < bb["lower"].iloc[-1] * 1.05
                rsi_ok = rsi_val < 45
                if (near_low and rsi_ok) or self._regime == "STRONG_BULL":
                    return Signal(action="BUY", symbol=symbol, date=date,
                                  price=current_price,
                                  reason=f"状态感知({self._regime}): 做多")

            elif "BEAR" in self._regime:
                # 等反弹到布林上轨+RSI高位
                near_high = current_price > bb["upper"].iloc[-1] * 0.95
                rsi_ok = rsi_val > 55
                if (near_high and rsi_ok) or self._regime == "STRONG_BEAR":
                    return Signal(action="SHORT", symbol=symbol, date=date,
                                  price=current_price,
                                  reason=f"状态感知({self._regime}): 做空")

        # === 平仓逻辑 ===
        if has_long:
            # 状态变熊或RSI超买
            if "BEAR" in self._regime or rsi_val > 75:
                return Signal(action="SELL", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"状态感知平多({self._regime})")

        if has_short:
            # 状态变牛或RSI超卖
            if "BULL" in self._regime or rsi_val < 25:
                return Signal(action="COVER", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"状态感知平空({self._regime})")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        return "BULL" in self._detect_regime(data)

    def sell_signal(self, data: pd.DataFrame) -> bool:
        return "BEAR" in self._detect_regime(data)
