"""
策略基类

所有策略需继承 BaseStrategy，实现以下方法：
- on_bar(i, data, portfolio) → Signal | None
- buy_signal(data) → bool
- sell_signal(data) → bool

内置常用技术指标计算方法（基于 pandas-ta）

多用户支持 (v5.1):
  传入 user_id 后自动从 strategy_configs 表加载该用户为此策略保存的自定义参数。
  使用 save_strategy_params() 保存参数。
"""

import json
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from src.models.strategy import Signal, StrategyConfig


def save_strategy_params(user_id: int, strategy_name: str, params_dict: dict) -> bool:
    """
    保存/更新用户对某策略的自定义参数到 strategy_configs 表。

    参数:
        user_id:        用户 ID
        strategy_name:  策略标识 (如 "ma_cross", "rsi", "contrarian_v1")
        params_dict:    参数字典 (如 {"fast_period": 10, "slow_period": 30})

    返回:
        True 表示保存成功
    """
    from src.database import SessionLocal
    from src.database.models import StrategyConfig as SC
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        existing = (
            db.query(SC)
            .filter_by(user_id=user_id, name=strategy_name)
            .first()
        )
        params_json = json.dumps(params_dict, ensure_ascii=False)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if existing:
            existing.config_json = params_json
            existing.updated_at = now
        else:
            new_sc = SC(
                user_id=user_id,
                name=strategy_name,
                config_json=params_json,
                created_at=now,
                updated_at=now,
            )
            db.add(new_sc)

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class BaseStrategy(ABC):
    """策略基类 — 所有策略的公共接口和工具方法"""

    def __init__(self, config: StrategyConfig = None, user_id: int = None,
                 _strategy_key: str = None):
        self.config = config or StrategyConfig()
        self.user_id = user_id
        self._strategy_key = _strategy_key or self.__class__.__name__
        # 从数据库加载用户自定义参数
        if user_id is not None:
            self._load_user_params()

    def _load_user_params(self):
        """
        查询 strategy_configs 表，如果该用户为此策略保存了自定义参数，
        则覆盖 config 中的对应属性。

        陷阱2: 比对版本戳。如果 DB 中 strategy_version < 策略类 VERSION，
        说明策略底层逻辑已更新，旧参数可能不兼容，丢弃并重置。
        """
        strategy_name = getattr(self, "_strategy_key", self.__class__.__name__)
        current_version = getattr(self, "VERSION", 1)
        try:
            from src.database import SessionLocal
            from src.database.models import StrategyConfig as SC

            db = SessionLocal()
            try:
                row = (
                    db.query(SC)
                    .filter_by(user_id=self.user_id, name=strategy_name, is_active=True)
                    .first()
                )
                if not row or not row.config_json:
                    return

                # 版本不匹配 → 重置为默认参数
                db_version = row.strategy_version or 1
                if db_version < current_version:
                    row.config_json = "{}"
                    row.strategy_version = current_version
                    db.commit()
                    return

                # 版本匹配 → 加载用户参数
                params = json.loads(row.config_json)
                for key, value in params.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            finally:
                db.close()
        except Exception:
            pass  # 数据库不可用时静默跳过，使用默认参数

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

    # ---- 浮点数安全比较 (陷阱3) ----

    @staticmethod
    def fp_gt(a: float, b: float, eps: float = 1e-8) -> bool:
        """安全大于: a > b + epsilon, 避免浮点精度导致信号闪烁"""
        return float(a) > float(b) + eps

    @staticmethod
    def fp_lt(a: float, b: float, eps: float = 1e-8) -> bool:
        """安全小于: a < b - epsilon"""
        return float(a) < float(b) - eps

    @staticmethod
    def fp_eq(a: float, b: float, eps: float = 1e-8) -> bool:
        """安全等于: abs(a-b) <= epsilon"""
        return abs(float(a) - float(b)) <= eps

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

    def cross_above(self, series1: pd.Series, series2: pd.Series,
                     eps: float = 1e-8) -> bool:
        """判断 series1 是否刚刚上穿 series2（最新两根 K 线）— 浮点安全"""
        if len(series1) < 2 or len(series2) < 2:
            return False
        return (not self.fp_gt(series1.iloc[-2], series2.iloc[-2], eps) and
                self.fp_gt(series1.iloc[-1], series2.iloc[-1], eps))

    def cross_below(self, series1: pd.Series, series2: pd.Series,
                     eps: float = 1e-8) -> bool:
        """判断 series1 是否刚刚下穿 series2 — 浮点安全"""
        if len(series1) < 2 or len(series2) < 2:
            return False
        return (not self.fp_lt(series1.iloc[-2], series2.iloc[-2], eps) and
                self.fp_lt(series1.iloc[-1], series2.iloc[-1], eps))

    @property
    def name(self) -> str:
        return self.config.name
