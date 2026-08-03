"""
微内核插件系统 (v7.0)

1. IStrategy / IFactor 标准接口
2. PluginManager 热插拔发现
3. DecisionReason 决策原因码
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Type
import pandas as pd
import os, sys, importlib, inspect


# ═══════════════════════════════════════════
# 决策原因码
# ═══════════════════════════════════════════

class DecisionReason(Enum):
    """所有买卖决策必须有原因码, 便于事后追溯"""

    # 技术信号
    REASON_MA_GOLDEN_CROSS = auto()       # 均线金叉
    REASON_MA_DEAD_CROSS = auto()         # 均线死叉
    REASON_RSI_OVERSOLD = auto()          # RSI超卖
    REASON_RSI_OVERBOUGHT = auto()        # RSI超买
    REASON_MACD_GOLDEN = auto()           # MACD金叉
    REASON_MACD_DEAD = auto()             # MACD死叉
    REASON_BOLL_LOWER = auto()            # 布林下轨
    REASON_BOLL_UPPER = auto()            # 布林上轨
    REASON_BREAKOUT = auto()              # 突破信号
    REASON_MEAN_REVERSION = auto()        # 均值回归

    # 风控
    REASON_TRAILING_STOP = auto()         # 移动止损
    REASON_DRAWDOWN_LIMIT = auto()        # 回撤熔断
    REASON_RISK_PARITY = auto()           # 风险平价调整
    REASON_POSITION_LIMIT = auto()        # 仓位上限

    # AI / 舆情
    REASON_AI_RECOMMEND = auto()          # AI推荐
    REASON_SENTIMENT_EXTREME = auto()     # 情绪极端(反向)
    REASON_AI_STRATEGY = auto()           # AI生成策略
    REASON_ENSEMBLE_VOTE = auto()         # 集成投票

    # 市场状态
    REASON_REGIME_SWITCH = auto()         # 市场状态切换
    REASON_BEAR_MARKET = auto()           # 熊市减仓
    REASON_BULL_MARKET = auto()           # 牛市加仓
    REASON_VOLATILITY_SPIKE = auto()      # 波动率飙升

    # 人工
    REASON_MANUAL = auto()                # 手动交易
    REASON_SCHEDULED = auto()             # 定时任务

    def to_code(self) -> str:
        return self.name

    @staticmethod
    def from_string(s: str):
        try:
            return DecisionReason[s]
        except KeyError:
            return DecisionReason.REASON_MANUAL


# ═══════════════════════════════════════════
# 标准接口
# ═══════════════════════════════════════════

class IStrategy(ABC):
    """策略插件接口 — 所有策略必须实现"""

    @abstractmethod
    def on_bar(self, i: int, data: pd.DataFrame,
               portfolio) -> Optional[object]:
        """每根K线调用, 返回 Signal 或 None"""
        ...

    @abstractmethod
    def buy_signal(self, data: pd.DataFrame) -> bool:
        """买入条件"""
        ...

    @abstractmethod
    def sell_signal(self, data: pd.DataFrame) -> bool:
        """卖出条件"""
        ...

    @property
    def reason_code(self) -> DecisionReason:
        """策略对应的默认原因码"""
        return DecisionReason.REASON_MANUAL

    @property
    def plugin_name(self) -> str:
        return self.__class__.__name__

    @property
    def plugin_version(self) -> str:
        return "1.0.0"


class IFactor(ABC):
    """因子插件接口 — 所有因子必须实现"""

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """输入 OHLCV, 输出因子值 Series (0~1)"""
        ...

    @property
    def factor_name(self) -> str:
        return self.__class__.__name__

    @property
    def category(self) -> str:
        return "composite"

    @property
    def description(self) -> str:
        return ""


# ═══════════════════════════════════════════
# PluginManager — 热插拔发现
# ═══════════════════════════════════════════

class PluginManager:
    """微内核插件管理器"""

    def __init__(self):
        self._strategies: Dict[str, Type[IStrategy]] = {}
        self._factors: Dict[str, Type[IFactor]] = {}
        self._strategy_instances: Dict[str, IStrategy] = {}

    def discover(self, search_paths: List[str] = None):
        """自动发现插件 + 导入现有策略库"""
        # 1. 导入现有策略
        try:
            from src.strategies.library import STRATEGIES
            for key, info in STRATEGIES.items():
                if info.get("class"):
                    self._strategies[key] = info["class"]
        except Exception:
            pass

        # 2. 导入现有因子
        try:
            from src.factors.definitions import FACTOR_REGISTRY
            for name, factor in FACTOR_REGISTRY.items():
                self._factors[name] = type(factor)
        except Exception:
            pass

        # 3. 文件系统扫描新插件
        if search_paths is None:
            base = os.path.dirname(os.path.dirname(__file__))
            search_paths = [
                os.path.join(base, "strategies"),
                os.path.join(base, "factors"),
            ]

        for sp in search_paths:
            if not os.path.isdir(sp):
                continue
            for fname in os.listdir(sp):
                if not fname.endswith(".py") or fname.startswith("_"):
                    continue
                mod_name = fname[:-3]
                try:
                    mod = importlib.import_module(
                        f"src.{os.path.basename(sp)}.{mod_name}")
                    for name, obj in inspect.getmembers(mod, inspect.isclass):
                        if obj.__module__ != mod.__name__:
                            continue
                        if issubclass(obj, IStrategy) and obj != IStrategy:
                            self._strategies[name] = obj
                        elif issubclass(obj, IFactor) and obj != IFactor:
                            self._factors[name] = obj
                except Exception:
                    pass

    def register_strategy(self, name: str, cls: Type[IStrategy]):
        self._strategies[name] = cls

    def register_factor(self, name: str, cls: Type[IFactor]):
        self._factors[name] = cls

    def get_strategy(self, name: str, **kwargs) -> IStrategy:
        if name not in self._strategies:
            raise KeyError(f"策略 {name} 未注册, 可用: {list(self._strategies.keys())}")
        inst = self._strategies[name](**kwargs)
        self._strategy_instances[name] = inst
        return inst

    def get_factor(self, name: str) -> IFactor:
        if name not in self._factors:
            raise KeyError(f"因子 {name} 未注册, 可用: {list(self._factors.keys())}")
        return self._factors[name]()

    def list_strategies(self) -> List[str]:
        return sorted(self._strategies.keys())

    def list_factors(self) -> List[str]:
        return sorted(self._factors.keys())

    def get_v2_strategy_registry(self):
        """Expose legacy plugins through the versioned V2 strategy contract."""
        from src.lxl_quantaxis.strategy.legacy import get_legacy_strategy_registry

        return get_legacy_strategy_registry()

    def get_v2_strategy_spec(self, name: str, version: str = None):
        """Resolve an existing plugin name to a V2 StrategySpec."""
        return self.get_v2_strategy_registry().get(f"legacy.{name}", version)

    def unload_strategy(self, name: str):
        """热卸载"""
        self._strategies.pop(name, None)
        self._strategy_instances.pop(name, None)

    def reload_plugin(self, mod_path: str):
        """热重载"""
        spec = importlib.util.spec_from_file_location(
            os.path.basename(mod_path), mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)


# 全局实例
plugin_mgr = PluginManager()
