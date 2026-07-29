"""
策略基类

所有策略需继承 BaseStrategy，实现以下方法：
- on_bar(i, data, portfolio) → Signal | None
- buy_signal(data) → bool
- sell_signal(data) → bool

内置常用技术指标计算方法（基于 pandas-ta）
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from src.models.strategy import Signal, StrategyConfig


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()

    @abstractmethod
    def on_bar(self, i: int, data: pd.DataFrame,
               portfolio) -> Optional[Signal]:
        """
        每根 K 线调用一次，返回交易信号

        参数:
            i: 当前数据索引
            data: 从第 0 行到第 i 行的完整 OHLCV 数据
            portfolio: 当前持仓对象
        """
        ...

    @abstractmethod
    def buy_signal(self, data: pd.DataFrame) -> bool:
        """判断当前是否应买入"""
        ...

    @abstractmethod
    def sell_signal(self, data: pd.DataFrame) -> bool:
        """判断当前是否应卖出"""
        ...

    # ---- 内置技术指标工具 ----

    def sma(self, data: pd.DataFrame, period: int = 20,
            column: str = "close") -> pd.Series:
        """简单移动平均线"""
        return data[column].rolling(window=period).mean()

    def ema(self, data: pd.DataFrame, period: int = 20,
            column: str = "close") -> pd.Series:
        """指数移动平均线"""
        return data[column].ewm(span=period, adjust=False).mean()

    def rsi(self, data: pd.DataFrame, period: int = 14,
            column: str = "close") -> pd.Series:
        """RSI 相对强弱指标"""
        delta = data[column].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    def macd(self, data: pd.DataFrame, fast: int = 12,
             slow: int = 26, signal: int = 9,
             column: str = "close") -> pd.DataFrame:
        """MACD 指标，返回 DataFrame(dif, dea, hist)"""
        ema_fast = self.ema(data, fast, column)
        ema_slow = self.ema(data, slow, column)
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2 * (dif - dea)
        return pd.DataFrame({"dif": dif, "dea": dea, "hist": hist})

    def bollinger(self, data: pd.DataFrame, period: int = 20,
                  std: float = 2.0,
                  column: str = "close") -> pd.DataFrame:
        """布林带，返回 DataFrame(upper, middle, lower)"""
        middle = self.sma(data, period, column)
        std_dev = data[column].rolling(window=period).std()
        upper = middle + std * std_dev
        lower = middle - std * std_dev
        return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})

    def atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 平均真实波幅"""
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def volume_sma(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """成交量均线"""
        return data["volume"].rolling(window=period).mean()

    def highest(self, data: pd.DataFrame, period: int = 20,
                column: str = "high") -> pd.Series:
        """N 日最高价"""
        return data[column].rolling(window=period).max()

    def lowest(self, data: pd.DataFrame, period: int = 20,
               column: str = "low") -> pd.Series:
        """N 日最低价"""
        return data[column].rolling(window=period).min()

    def cross_above(self, series1: pd.Series, series2: pd.Series) -> bool:
        """判断 series1 是否刚刚上穿 series2（最新两根 K 线）"""
        if len(series1) < 2 or len(series2) < 2:
            return False
        return (series1.iloc[-2] <= series2.iloc[-2] and
                series1.iloc[-1] > series2.iloc[-1])

    def cross_below(self, series1: pd.Series, series2: pd.Series) -> bool:
        """判断 series1 是否刚刚下穿 series2"""
        if len(series1) < 2 or len(series2) < 2:
            return False
        return (series1.iloc[-2] >= series2.iloc[-2] and
                series1.iloc[-1] < series2.iloc[-1])

    @property
    def name(self) -> str:
        return self.config.name
