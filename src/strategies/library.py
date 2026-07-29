"""
策略库 — 完整的常用量化策略

内置策略:
  1. MACrossStrategy      — 双均线交叉（金叉/死叉）
  2. RSIStrategy          — RSI 超买超卖
  3. MACDStrategy         — MACD 金叉死叉
  4. BollingerStrategy    — 布林带突破
  5. TurtleStrategy       — 海龟交易法则（唐奇安通道突破）
  6. MeanReversionStrategy — 均值回归（布林带 + RSI 组合）
  7. MomentumStrategy     — 动量策略（突破 N 日最高点买入）

每个策略可直接实例化后传入 BacktestEngine.run()
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from src.models.strategy import Signal, StrategyConfig


class BaseStrategy(ABC):
    """策略基类 — 所有策略的公共接口和工具方法"""

    def __init__(self, config: StrategyConfig = None,
                 use_trend_filter: bool = False,
                 trend_ma_period: int = 200,
                 use_trailing_stop: bool = False,
                 trailing_atr_mult: float = 3.0):
        self.config = config or StrategyConfig()
        self.use_trend_filter = use_trend_filter
        self.trend_ma_period = trend_ma_period
        self.use_trailing_stop = use_trailing_stop
        self.trailing_atr_mult = trailing_atr_mult
        self._entry_price = 0
        self._highest_since_entry = 0

    @abstractmethod
    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        """每根 K 线调用一次，返回交易信号或 None"""
        ...

    @abstractmethod
    def buy_signal(self, data: pd.DataFrame) -> bool:
        """判断是否触发买入"""
        ...

    @abstractmethod
    def sell_signal(self, data: pd.DataFrame) -> bool:
        """判断是否触发卖出"""
        ...

    # ---- 风控增强 (v4.1) ----

    def is_uptrend(self, data: pd.DataFrame) -> bool:
        """趋势过滤: 价格在长期均线之上才允许做多"""
        if not self.use_trend_filter:
            return True
        if len(data) < self.trend_ma_period:
            return True  # 数据不足时不过滤
        ma = self.sma(data, self.trend_ma_period)
        return data["close"].iloc[-1] > ma.iloc[-1]

    def trailing_stop_price(self, data: pd.DataFrame) -> float:
        """计算移动止损价"""
        if not self.use_trailing_stop or self._entry_price <= 0:
            return 0
        atr_val = self.atr(data, 14).iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            return 0
        current_high = data["high"].iloc[-1]
        self._highest_since_entry = max(self._highest_since_entry, current_high)
        return self._highest_since_entry - self.trailing_atr_mult * atr_val

    def set_entry(self, price: float):
        self._entry_price = price
        self._highest_since_entry = price

    def clear_entry(self):
        self._entry_price = 0
        self._highest_since_entry = 0

    # ---- 技术指标工具 ----

    def sma(self, data: pd.DataFrame, period: int = 20,
            column: str = "close") -> pd.Series:
        return data[column].rolling(window=period).mean()

    def ema(self, data: pd.DataFrame, period: int = 20,
            column: str = "close") -> pd.Series:
        return data[column].ewm(span=period, adjust=False).mean()

    def rsi(self, data: pd.DataFrame, period: int = 14,
            column: str = "close") -> pd.Series:
        delta = data[column].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    def macd(self, data: pd.DataFrame, fast: int = 12,
             slow: int = 26, signal: int = 9,
             column: str = "close") -> pd.DataFrame:
        ema_fast = self.ema(data, fast, column)
        ema_slow = self.ema(data, slow, column)
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2 * (dif - dea)
        return pd.DataFrame({"dif": dif, "dea": dea, "hist": hist})

    def bollinger(self, data: pd.DataFrame, period: int = 20,
                  std: float = 2.0,
                  column: str = "close") -> pd.DataFrame:
        middle = self.sma(data, period, column)
        std_dev = data[column].rolling(window=period).std()
        upper = middle + std * std_dev
        lower = middle - std * std_dev
        return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})

    def atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / period, adjust=False).mean()

    def volume_sma(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data["volume"].rolling(window=period).mean()

    def highest(self, data: pd.DataFrame, period: int = 20,
                column: str = "high") -> pd.Series:
        return data[column].rolling(window=period).max()

    def lowest(self, data: pd.DataFrame, period: int = 20,
               column: str = "low") -> pd.Series:
        return data[column].rolling(window=period).min()

    def cross_above(self, s1: pd.Series, s2: pd.Series) -> bool:
        if len(s1) < 2 or len(s2) < 2:
            return False
        return (s1.iloc[-2] <= s2.iloc[-2] and s1.iloc[-1] > s2.iloc[-1])

    def cross_below(self, s1: pd.Series, s2: pd.Series) -> bool:
        if len(s1) < 2 or len(s2) < 2:
            return False
        return (s1.iloc[-2] >= s2.iloc[-2] and s1.iloc[-1] < s2.iloc[-1])

    @property
    def name(self) -> str:
        return self.config.name or self.__class__.__name__


# ============================================================
# 1. 双均线交叉策略
# ============================================================

class MACrossStrategy(BaseStrategy):
    """
    双均线交叉策略

    参数:
        fast_period: 快线周期 (默认 5)
        slow_period: 慢线周期 (默认 20)
        vol_confirm: 是否需要成交量放大确认
        vol_ratio: 成交量放大倍数
    """

    def __init__(self, fast_period: int = 5, slow_period: int = 20,
                 vol_confirm: bool = False, vol_ratio: float = 1.2,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.vol_confirm = vol_confirm
        self.vol_ratio = vol_ratio

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.slow_period + 1:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            if not self.is_uptrend(data):
                return None  # 趋势过滤
            self.set_entry(current_price)
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"金叉(趋势确认): MA{self.fast_period}>MA{self.slow_period}")

        if has_position:
            # 移动止损
            stop_px = self.trailing_stop_price(data)
            if stop_px > 0 and current_price < stop_px:
                self.clear_entry()
                return Signal(action="SELL", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"移动止损: {stop_px:.2f}")

            if self.sell_signal(data):
                self.clear_entry()
                return Signal(action="SELL", symbol=symbol, date=date,
                              price=current_price,
                              reason=f"死叉: MA{self.fast_period}<MA{self.slow_period}")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        fast_ma = self.sma(data, self.fast_period)
        slow_ma = self.sma(data, self.slow_period)
        if not self.cross_above(fast_ma, slow_ma):
            return False
        if self.vol_confirm:
            vol_ma = self.volume_sma(data, 20)
            if len(vol_ma) < 2:
                return False
            return data["volume"].iloc[-1] >= vol_ma.iloc[-1] * self.vol_ratio
        return True

    def sell_signal(self, data: pd.DataFrame) -> bool:
        fast_ma = self.sma(data, self.fast_period)
        slow_ma = self.sma(data, self.slow_period)
        return self.cross_below(fast_ma, slow_ma)


# ============================================================
# 2. RSI 超买超卖策略
# ============================================================

class RSIStrategy(BaseStrategy):
    """
    RSI 策略

    参数:
        rsi_period: RSI 计算周期 (默认 14)
        oversold: 超卖阈值，低于此值买入 (默认 30)
        overbought: 超买阈值，高于此值卖出 (默认 70)
        require_recovery: 是否等待 RSI 回到正常区间再下单
    """

    def __init__(self, rsi_period: int = 14, oversold: float = 30,
                 overbought: float = 70, require_recovery: bool = True,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.require_recovery = require_recovery

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.rsi_period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"RSI超卖反弹: RSI<{self.oversold}")

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"RSI超买回落: RSI>{self.overbought}")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        rsi = self.rsi(data, self.rsi_period)
        if len(rsi) < 3:
            return False
        # RSI 从超卖区回升
        if self.require_recovery:
            return (rsi.iloc[-2] <= self.oversold and rsi.iloc[-1] > self.oversold)
        return rsi.iloc[-1] < self.oversold

    def sell_signal(self, data: pd.DataFrame) -> bool:
        rsi = self.rsi(data, self.rsi_period)
        if len(rsi) < 3:
            return False
        if self.require_recovery:
            return (rsi.iloc[-2] >= self.overbought and rsi.iloc[-1] < self.overbought)
        return rsi.iloc[-1] > self.overbought


# ============================================================
# 3. MACD 策略
# ============================================================

class MACDStrategy(BaseStrategy):
    """
    MACD 金叉死叉策略

    参数:
        fast: 快线周期 (12)
        slow: 慢线周期 (26)
        signal: 信号线周期 (9)
        filter_zero: 是否只在水上做多 / 水下做空
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9,
                 filter_zero: bool = True, config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.filter_zero = filter_zero

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.slow + self.signal + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions
        macd_df = self.macd(data, self.fast, self.slow, self.signal)

        if not has_position and self.buy_signal(data):
            reason = f"MACD金叉: DIF上穿DEA"
            if self.filter_zero:
                reason += f" (零轴上)"
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price, reason=reason)

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price, reason="MACD死叉: DIF下穿DEA")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        macd = self.macd(data, self.fast, self.slow, self.signal)
        if len(macd) < 2:
            return False
        cross = self.cross_above(macd["dif"], macd["dea"])
        if self.filter_zero:
            return cross and macd["dea"].iloc[-1] > 0
        return cross

    def sell_signal(self, data: pd.DataFrame) -> bool:
        macd = self.macd(data, self.fast, self.slow, self.signal)
        return self.cross_below(macd["dif"], macd["dea"])


# ============================================================
# 4. 布林带策略
# ============================================================

class BollingerStrategy(BaseStrategy):
    """
    布林带策略

    参数:
        period: 均线周期 (20)
        std_dev: 标准差倍数 (2.0)
        buy_on_lower: 触及下轨反弹买入
        sell_on_middle: 回到中轨卖出
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0,
                 buy_on_lower: bool = True, sell_on_middle: bool = True,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.period = period
        self.std_dev = std_dev
        self.buy_on_lower = buy_on_lower
        self.sell_on_middle = sell_on_middle

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price, reason="布林带下轨反弹")

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price, reason="布林带上轨/中轨卖出")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        boll = self.bollinger(data, self.period, self.std_dev)
        if len(boll) < 3:
            return False
        close = data["close"]
        # 前一日收盘价 <= 下轨，当前收盘价 > 下轨（反弹确认）
        return (close.iloc[-2] <= boll["lower"].iloc[-2] and
                close.iloc[-1] > boll["lower"].iloc[-1])

    def sell_signal(self, data: pd.DataFrame) -> bool:
        boll = self.bollinger(data, self.period, self.std_dev)
        if len(boll) < 3:
            return False
        close = data["close"]
        if self.sell_on_middle:
            # 跌破中轨
            return self.cross_below(close, boll["middle"])
        # 触及上轨回落
        return (close.iloc[-2] >= boll["upper"].iloc[-2] and
                close.iloc[-1] < boll["upper"].iloc[-1])


# ============================================================
# 5. 海龟交易策略
# ============================================================

class TurtleStrategy(BaseStrategy):
    """
    海龟交易法则（简化版）

    使用唐奇安通道突破:
      - 买入: 价格突破 N 日最高点
      - 卖出: 价格跌破 M 日最低点
      - 止损: 跌破 2*ATR
      - 加仓: 每上涨 0.5*ATR 加仓一次（最多 4 次）

    参数:
        entry_period: 入场通道周期 (20)
        exit_period: 离场通道周期 (10)
        atr_period: ATR 周期 (20)
        atr_stop: ATR 止损倍数 (2.0)
    """

    def __init__(self, entry_period: int = 20, exit_period: int = 10,
                 atr_period: int = 20, atr_stop: float = 2.0,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_period = atr_period
        self.atr_stop = atr_stop
        self._entry_price = 0

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.entry_period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            self._entry_price = current_price
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"海龟突破: {self.entry_period}日高点")

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"海龟离场: {self.exit_period}日低点")

        # ATR 止损
        if has_position and self._entry_price > 0:
            atr_val = self.atr(data, self.atr_period).iloc[-1]
            stop_price = self._entry_price - self.atr_stop * atr_val
            if current_price <= stop_price:
                return Signal(action="SELL", symbol=symbol, date=date,
                              price=current_price, reason=f"ATR止损: {stop_price:.2f}")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        highest_n = self.highest(data, self.entry_period)
        if len(highest_n) < 2:
            return False
        return (data["close"].iloc[-2] <= highest_n.iloc[-2] and
                data["close"].iloc[-1] > highest_n.iloc[-2])

    def sell_signal(self, data: pd.DataFrame) -> bool:
        lowest_m = self.lowest(data, self.exit_period, "close")
        if len(lowest_m) < 2:
            return False
        return data["close"].iloc[-1] < lowest_m.iloc[-2]


# ============================================================
# 6. 均值回归策略
# ============================================================

class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略

    逻辑:
      - 价格偏离 20 日均线超过 N% 时逆势入场
      - 配合 RSI 确认超买超卖
      - 回归均线附近时离场

    参数:
        ma_period: 均线周期 (20)
        deviation_pct: 偏离百分比阈值 (3.0)
        rsi_period: RSI 周期 (14)
        rsi_extreme: RSI 极端阈值 (30/70)
    """

    def __init__(self, ma_period: int = 20, deviation_pct: float = 3.0,
                 rsi_period: int = 14, rsi_extreme: float = 30,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.ma_period = ma_period
        self.deviation_pct = deviation_pct
        self.rsi_period = rsi_period
        self.rsi_extreme = rsi_extreme

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.ma_period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"均值回归买入: 偏离均线->{self.deviation_pct}%")

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price,
                          reason="回归均线卖出")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        close = data["close"]
        ma = self.sma(data, self.ma_period)
        if len(ma) < 2 or pd.isna(ma.iloc[-1]):
            return False
        deviation = (close.iloc[-1] - ma.iloc[-1]) / ma.iloc[-1] * 100
        rsi_val = self.rsi(data, self.rsi_period).iloc[-1]
        return deviation < -self.deviation_pct and rsi_val < self.rsi_extreme + 10

    def sell_signal(self, data: pd.DataFrame) -> bool:
        close = data["close"]
        ma = self.sma(data, self.ma_period)
        if len(ma) < 2 or pd.isna(ma.iloc[-1]):
            return False
        deviation = (close.iloc[-1] - ma.iloc[-1]) / ma.iloc[-1] * 100
        # 回到均线上方或接近均线
        return deviation >= -self.deviation_pct * 0.3


# ============================================================
# 7. 动量突破策略
# ============================================================

class MomentumStrategy(BaseStrategy):
    """
    动量策略

    逻辑:
      - 价格突破 N 日高点 + 成交量放大 = 买入
      - 价格跌破 M 日低点 = 卖出
      - 可叠加趋势过滤（长期均线方向）

    参数:
        breakout_period: 突破周期 (20)
        exit_period: 离场周期 (10)
        volume_confirm: 需成交量确认
        trend_filter: 是否用长期均线过滤方向
    """

    def __init__(self, breakout_period: int = 20, exit_period: int = 10,
                 volume_confirm: bool = False, trend_filter: bool = False,
                 config: StrategyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self.breakout_period = breakout_period
        self.exit_period = exit_period
        self.volume_confirm = volume_confirm
        self.trend_filter = trend_filter

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[Signal]:
        if i < self.breakout_period + 2:
            return None

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"动量突破: {self.breakout_period}日高点")

        if has_position and self.sell_signal(data):
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price,
                          reason=f"动量离场: {self.exit_period}日低点")

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        close = data["close"]
        highest_n = self.highest(data, self.breakout_period)
        if len(highest_n) < 3 or pd.isna(highest_n.iloc[-3]):
            return False

        # 突破确认: 前一日收盘 <= 前一日N日高点，当日收盘 > 前一日N日高点
        breakout = (close.iloc[-2] <= highest_n.iloc[-2] and
                    close.iloc[-1] > highest_n.iloc[-2])

        if not breakout:
            return False

        # 成交量确认
        if self.volume_confirm:
            vol_ma = self.volume_sma(data, 20)
            if len(vol_ma) < 2 or pd.isna(vol_ma.iloc[-1]):
                return False
            if data["volume"].iloc[-1] < vol_ma.iloc[-1] * 1.2:
                return False

        # 趋势过滤：价格在 50 日均线上方才做多
        if self.trend_filter:
            ma50 = self.sma(data, 50)
            if len(ma50) < 1 or pd.isna(ma50.iloc[-1]):
                return False
            if close.iloc[-1] < ma50.iloc[-1]:
                return False

        return True

    def sell_signal(self, data: pd.DataFrame) -> bool:
        lowest_m = self.lowest(data, self.exit_period, "close")
        if len(lowest_m) < 2:
            return False
        return data["close"].iloc[-1] < lowest_m.iloc[-2]


# ============================================================
# 策略注册表
# ============================================================

from src.strategies.adaptive import AdaptiveCompositeStrategy
from src.strategies.short_strategies import TrendShortStrategy, DualDirectionStrategy
from src.strategies.regime_strategy import RegimeAwareStrategy

STRATEGIES = {
    "adaptive": {
        "name": "自适应复合",
        "class": AdaptiveCompositeStrategy,
        "params": {},
        "description": "自动检测趋势/震荡/下跌, 切换最优子策略",
    },
    "trend_short": {
        "name": "趋势破位做空",
        "class": TrendShortStrategy,
        "params": {"short_period": (10, 30), "cover_period": (5, 20)},
        "description": "价格破位做空+回升平仓, 适合下跌趋势",
    },
    "dual_direction": {
        "name": "双向交易",
        "class": DualDirectionStrategy,
        "params": {},
        "description": "趋势向上做多, 趋势向下做空, 双向获利",
    },
    "regime_aware": {
        "name": "状态感知",
        "class": RegimeAwareStrategy,
        "params": {},
        "description": "5状态分类(强牛/弱牛/震荡/弱熊/强熊), 自适应双向交易",
    },
    "ma_cross": {
        "name": "双均线交叉",
        "class": MACrossStrategy,
        "params": {
            "fast_period": (3, 30),
            "slow_period": (10, 60),
            "vol_confirm": [True, False],
        },
        "description": "短期均线上穿长期均线买入，下穿卖出",
    },
    "rsi": {
        "name": "RSI 超买超卖",
        "class": RSIStrategy,
        "params": {
            "rsi_period": (7, 21),
            "oversold": (20, 40),
            "overbought": (60, 80),
        },
        "description": "RSI 低于超卖线买入，高于超买线卖出",
    },
    "macd": {
        "name": "MACD 金叉死叉",
        "class": MACDStrategy,
        "params": {
            "fast": (8, 20),
            "slow": (20, 40),
            "signal": (5, 15),
        },
        "description": "MACD DIF 上穿 DEA 买入，下穿卖出",
    },
    "bollinger": {
        "name": "布林带",
        "class": BollingerStrategy,
        "params": {
            "period": (10, 40),
            "std_dev": (1.5, 3.0),
        },
        "description": "价格触及下轨反弹买入，触及上轨/中轨卖出",
    },
    "turtle": {
        "name": "海龟交易",
        "class": TurtleStrategy,
        "params": {
            "entry_period": (10, 55),
            "exit_period": (5, 30),
            "atr_stop": (1.0, 3.0),
        },
        "description": "突破 N 日高点买入，跌破 M 日低点卖出，ATR 止损",
    },
    "mean_reversion": {
        "name": "均值回归",
        "class": MeanReversionStrategy,
        "params": {
            "ma_period": (10, 40),
            "deviation_pct": (1.5, 5.0),
            "rsi_extreme": (20, 40),
        },
        "description": "价格远离均线时逆势入场，回归均线离场",
    },
    "momentum": {
        "name": "动量突破",
        "class": MomentumStrategy,
        "params": {
            "breakout_period": (10, 50),
            "exit_period": (5, 25),
        },
        "description": "突破 N 日高点买入，配合成交量 + 趋势过滤",
    },
}


def get_strategy_class(name: str):
    """根据名称获取策略类"""
    if name in STRATEGIES:
        return STRATEGIES[name]["class"]
    raise KeyError(f"未知策略: {name}，可选: {list(STRATEGIES.keys())}")


def list_strategies():
    """列出所有可用策略"""
    print("\n  可用策略：")
    for key, info in STRATEGIES.items():
        print(f"    {key:<20} — {info['description']}")
