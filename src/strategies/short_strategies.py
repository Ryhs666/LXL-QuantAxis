"""
做空策略 (v4.6)
A股虽然没有直接做空，但可以通过策略信号提示卖点
支持: 趋势破位做空、均线死叉做空
"""

from typing import Optional
import pandas as pd
from src.models.strategy import Signal, StrategyConfig
from src.strategies.library import BaseStrategy


class TrendShortStrategy(BaseStrategy):
    """趋势破位做空策略: 价格跌破关键支撑做空, 回升到均线上方平仓"""

    def __init__(self, short_period: int = 20, cover_period: int = 10,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.short_period = short_period
        self.cover_period = cover_period

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.short_period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        short_key = "SHORT_" + symbol
        has_short = short_key in portfolio.positions
        has_long = symbol in portfolio.positions

        if not has_short and not has_long:
            # 破位做空: 价格跌破N日低点且低于均线
            lowest_n = self.lowest(data, self.short_period, "close")
            ma60 = self.sma(data, 60)
            if len(lowest_n) >= 2 and len(ma60) >= 2:
                if (data["close"].iloc[-2] >= lowest_n.iloc[-2] and
                    current_price < lowest_n.iloc[-2] and
                    current_price < ma60.iloc[-1]):
                    return Signal(action="SHORT", symbol=symbol, date=date,
                                  price=current_price,
                                  reason=f"破位做空: 跌破{self.short_period}日低点+60MA下方")

        if has_short:
            # 平空: 价格回升突破M日高点
            highest_m = self.highest(data, self.cover_period, "close")
            if self.cross_above(data["close"], highest_m):
                self.clear_entry()
                return Signal(action="COVER", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"平空: 回升突破{self.cover_period}日高点")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        return False

    def sell_signal(self, data: pd.DataFrame) -> bool:
        return False


class DualDirectionStrategy(BaseStrategy):
    """双向交易策略: 趋势向上做多, 趋势向下做空, 震荡不动"""

    def __init__(self, config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < 60:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]

        has_long = symbol in portfolio.positions
        has_short = ("SHORT_" + symbol) in portfolio.positions

        ma20 = self.sma(data, 20)
        ma60 = self.sma(data, 60)
        rsi_val = self.rsi(data, 14).iloc[-1]

        # 趋势判定 (放宽: 只要MA方向一致即可)
        trend_up = ma20.iloc[-1] > ma60.iloc[-1]
        trend_down = ma20.iloc[-1] < ma60.iloc[-1]

        # 开仓
        if not has_long and not has_short:
            if trend_up:
                self.set_entry(current_price)
                return Signal(action="BUY", symbol=symbol, date=date,
                              price=current_price, reason=f"双向:上升趋势(MA20>MA60)")

            elif trend_down:
                self.set_entry(current_price)
                return Signal(action="SHORT", symbol=symbol, date=date,
                              price=current_price, reason=f"双向:下降趋势(MA20<MA60)")

        # 平仓: 趋势反转
        if has_long and trend_down:
            self.clear_entry()
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price, reason="双向:趋势反转向下,平多")

        if has_short and trend_up:
            self.clear_entry()
            return Signal(action="COVER", symbol=symbol, date=date,
                          price=current_price, reason="双向:趋势反转向上,平空")

        # 止损: RSI极端
        if has_long and rsi_val > 80:
            self.clear_entry()
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price, reason="双向:RSI超买止损")

        if has_short and rsi_val < 20:
            self.clear_entry()
            return Signal(action="COVER", symbol=symbol, date=date,
                          price=current_price, reason="双向:RSI超卖止损")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        return False

    def sell_signal(self, data: pd.DataFrame) -> bool:
        return False
