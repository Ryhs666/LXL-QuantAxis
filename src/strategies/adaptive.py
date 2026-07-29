"""
自适应复合策略 (v4.5)
自动检测市场状态，切换最佳子策略，解决震荡市表现差的问题

三种市场状态:
  TRENDING_UP   → 追趋势 (momentum/turtle)
  RANGING       → 均值回归 (bollinger/mean_reversion)
  TRENDING_DOWN → 空仓/逆势 (cash/contrarian)

状态检测: 使用 ADX + 布林宽度 + MA斜率 三因子判定
"""

from typing import Optional
import pandas as pd
from src.models.strategy import Signal, StrategyConfig
from src.strategies.library import BaseStrategy


class AdaptiveCompositeStrategy(BaseStrategy):
    """自适应复合策略 — 自动切换最佳子策略"""

    def __init__(self, config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self._current_regime = "RANGING"
        self._regime_counter = 0

    def _detect_regime(self, data: pd.DataFrame) -> str:
        """检测当前市场状态"""
        if len(data) < 60:
            return "RANGING"

        close = data["close"]

        # 1. ADX-like 趋势强度
        trend = self._calc_adx(data, 14)

        # 2. 布林宽度 (波动预期)
        boll = self.bollinger(data, 20, 2.0)
        bb_width = (boll["upper"].iloc[-1] - boll["lower"].iloc[-1]) / boll["middle"].iloc[-1]

        # 3. MA 斜率
        ma20 = self.sma(data, 20)
        ma_slope = (ma20.iloc[-1] / ma20.iloc[-5] - 1) if len(ma20) >= 5 else 0

        # 判定
        if trend > 25 and ma_slope > 0.005:
            return "TRENDING_UP"
        elif trend > 25 and ma_slope < -0.005:
            return "TRENDING_DOWN"
        elif bb_width < 0.05 and trend < 20:
            return "RANGING"
        else:
            return self._current_regime  # 保持上次状态

    def _calc_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """简化 ADX 计算"""
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()

        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = pd.Series(0.0, index=data.index)
        minus_dm = pd.Series(0.0, index=data.index)
        plus_dm[(up > down) & (up > 0)] = up
        minus_dm[(down > up) & (down > 0)] = down

        plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, 1))
        minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, 1))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()

        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 15.0

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < 60:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        # 检测状态
        self._current_regime = self._detect_regime(data)

        if not has_position:
            signal = self._buy_signal_for_regime(data)
            if signal:
                return Signal(action="BUY", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"自适应({self._current_regime}): {signal}")

        if has_position:
            sell_reason = self._sell_signal_for_regime(data)
            if sell_reason:
                return Signal(action="SELL", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"自适应({self._current_regime}): {sell_reason}")

        return None

    def _buy_signal_for_regime(self, data: pd.DataFrame) -> Optional[str]:
        """根据状态生成买入信号"""
        close = data["close"]

        if self._current_regime == "TRENDING_UP":
            # 追趋势: 突破20日高点
            hh = self.highest(data, 20)
            if close.iloc[-1] > hh.iloc[-2]:
                return "突破20日高点"
            # 或均线金叉
            ma5 = self.sma(data, 5)
            ma20 = self.sma(data, 20)
            if self.cross_above(ma5, ma20):
                return "MA5上穿MA20"

        elif self._current_regime == "RANGING":
            # 均值回归: RSI超卖 + 布林下轨
            rsi_val = self.rsi(data, 14).iloc[-1]
            boll = self.bollinger(data, 20, 2.0)
            if rsi_val < 35 and close.iloc[-1] < boll["lower"].iloc[-1]:
                return f"RSI超卖({rsi_val:.0f})+布林下轨"

        elif self._current_regime == "TRENDING_DOWN":
            # 下跌趋势: 只在极度超卖时抄底
            rsi_val = self.rsi(data, 14).iloc[-1]
            boll = self.bollinger(data, 20, 2.5)
            if rsi_val < 25 and close.iloc[-1] < boll["lower"].iloc[-1]:
                return f"极端超卖反弹(RSI={rsi_val:.0f})"

        return None

    def _sell_signal_for_regime(self, data: pd.DataFrame) -> Optional[str]:
        """根据状态生成卖出信号"""
        close = data["close"]
        rsi_val = self.rsi(data, 14).iloc[-1]

        if self._current_regime == "TRENDING_UP":
            # 趋势减弱
            ma5 = self.sma(data, 5)
            ma20 = self.sma(data, 20)
            if self.cross_below(ma5, ma20):
                return "MA5下穿MA20"

        elif self._current_regime == "RANGING":
            # 回归均线或RSI超买
            boll = self.bollinger(data, 20, 2.0)
            if close.iloc[-1] > boll["middle"].iloc[-1] and rsi_val > 55:
                return "回归中轨+RSI中性"
            if rsi_val > 70:
                return f"RSI超买({rsi_val:.0f})"

        elif self._current_regime == "TRENDING_DOWN":
            # 快进快出
            if rsi_val > 50:
                return "反弹到位,快出"

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        return self._buy_signal_for_regime(data) is not None

    def sell_signal(self, data: pd.DataFrame) -> bool:
        return self._sell_signal_for_regime(data) is not None
