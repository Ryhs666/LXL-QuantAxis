"""
信号组合器 — 属于你自己的策略引擎

核心理念: 策略 = 因子 + 逻辑 + 阈值

使用方式:
    1. 选择因子 (从因子库挑选)
    2. 设定条件 (每个因子的触发条件)
    3. 组合逻辑 (AND/OR/加权评分)
    4. 生成信号

示例:
    composer = SignalComposer()
    composer.add_condition("rsi_norm", "lt", 0.3, weight=2)     # RSI超卖，权重2
    composer.add_condition("ma_deviation", "lt", -0.02, weight=1) # 偏离均线
    composer.set_logic("weighted", threshold=2.0)                 # 加权分>=2触发
    signal = composer.evaluate(data)

    # 或者用链式 API:
    signal = (SignalComposer()
        .rsi_oversold(14, 30)
        .volume_surge(1.5)
        .with_logic("and")
        .evaluate(data))
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
import pandas as pd
import numpy as np

from src.factors.definitions import FactorCalculator
from src.models.strategy import Signal, StrategyConfig


@dataclass
class Condition:
    """一个信号条件"""
    factor: str               # 因子名
    operator: str             # "gt" | "lt" | "cross_above" | "cross_below" | "between"
    threshold: float          # 阈值
    threshold2: Optional[float] = None  # between 的第二个阈值
    weight: float = 1.0       # 权重（weighted 模式使用）
    decay_factor: float = 1.0  # IC衰减系数 (1.0=正常, 0.0=禁用, 0.3=严重衰减)


@dataclass
class SignalRule:
    """一条完整的信号规则 — 买入或卖出的条件组合"""
    conditions: List[Condition] = field(default_factory=list)
    logic: str = "and"          # "and" | "or" | "weighted"
    threshold: float = 0.5      # weighted 模式的总分阈值
    action: str = "BUY"         # "BUY" | "SELL"
    description: str = ""       # 这条规则的描述


class SignalComposer:
    """
    信号组合器 — 搭建你自己的交易策略

    三种逻辑模式:
      - "and": 所有条件都满足 → 触发
      - "or":  任意条件满足 → 触发
      - "weighted": 加权评分 >= threshold → 触发
    """

    def __init__(self, name: str = "CustomStrategy"):
        self.name = name
        self.buy_rules: List[SignalRule] = []
        self.sell_rules: List[SignalRule] = []
        self._current_rule: Optional[SignalRule] = None

    # ---- 链式 API: 快捷条件定义 ----

    def rsi_oversold(self, period: int = 14, threshold: float = 30, weight: float = 2.0):
        """RSI 超卖"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("rsi_norm", "lt", threshold / 100, weight=weight))
        return self

    def rsi_overbought(self, period: int = 14, threshold: float = 70, weight: float = 2.0):
        """RSI 超买"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("rsi_norm", "gt", threshold / 100, weight=weight))
        return self

    def price_below_ma(self, period: int = 20, weight: float = 1.0):
        """价格低于均线"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("ma_deviation", "lt", -0.1, weight=weight))
        return self

    def price_above_ma(self, period: int = 20, weight: float = 1.0):
        """价格高于均线"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("ma_deviation", "gt", 0.1, weight=weight))
        return self

    def ma_golden_cross(self, fast: int = 5, slow: int = 20, weight: float = 2.0):
        """均线金叉"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("ma_alignment", "cross_above", 0.5, weight=weight))
        return self

    def ma_dead_cross(self, fast: int = 5, slow: int = 20, weight: float = 2.0):
        """均线死叉"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("ma_alignment", "cross_below", 0.5, weight=weight))
        return self

    def volume_surge(self, ratio: float = 1.5, weight: float = 1.0):
        """放量"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("volume_ratio", "gt", ratio, weight=weight))
        return self

    def momentum_strong(self, weight: float = 1.5):
        """动量强劲"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("momentum_score", "gt", 0.6, weight=weight))
        return self

    def momentum_weak(self, weight: float = 1.5):
        """动量衰竭"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("momentum_score", "lt", 0.4, weight=weight))
        return self

    def trend_strong(self, weight: float = 1.5):
        """趋势强劲"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("trend_strength", "gt", 0.3, weight=weight))
        return self

    def trend_weak(self, weight: float = 1.5):
        """趋势结束"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("trend_strength", "lt", 0.2, weight=weight))
        return self

    def hammer_pattern(self, weight: float = 1.0):
        """锤子线反转"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("hammer", "gt", 0.5, weight=weight))
        return self

    def near_bollinger_low(self, weight: float = 1.5):
        """接近布林下轨"""
        self._get_or_create_rule("BUY").conditions.append(
            Condition("bollinger_pos", "lt", 0.2, weight=weight))
        return self

    def near_bollinger_high(self, weight: float = 1.5):
        """接近布林上轨"""
        self._get_or_create_rule("SELL").conditions.append(
            Condition("bollinger_pos", "gt", 0.8, weight=weight))
        return self

    # ---- 通用 API ----

    def add_condition(self, factor: str, operator: str,
                      threshold: float, threshold2: float = None,
                      weight: float = 1.0, action: str = "BUY"):
        """
        添加条件

        factor: 因子名 (见 FACTOR_REGISTRY)
        operator: "gt" 大于 / "lt" 小于 / "cross_above" 上穿 / "cross_below" 下穿 / "between" 区间
        threshold: 阈值
        weight: 权重
        """
        rule = self._get_or_create_rule(action)
        rule.conditions.append(
            Condition(factor, operator, threshold, threshold2, weight))
        return self

    def set_logic(self, logic: str, threshold: float = 0.5, action: str = "BUY"):
        """
        设置组合逻辑

        logic: "and" | "or" | "weighted"
        threshold: weighted 模式的触发阈值
        """
        rule = self._get_or_create_rule(action)
        rule.logic = logic
        rule.threshold = threshold
        return self

    def with_logic(self, logic: str, threshold: float = 0.5):
        """设置买入和卖出都用同一个逻辑"""
        for action in ["BUY", "SELL"]:
            if self._get_rule(action):
                self.set_logic(logic, threshold, action)
        return self

    def describe(self, action: str = "BUY") -> str:
        """生成规则描述"""
        rule = self._get_rule(action)
        if not rule or not rule.conditions:
            return f"{action}: 无条件"
        parts = []
        for c in rule.conditions:
            op_map = {"gt": ">", "lt": "<", "cross_above": "上穿", "cross_below": "下穿"}
            op = op_map.get(c.operator, c.operator)
            parts.append(f"{c.factor} {op} {c.threshold}(w={c.weight})")
        logic_map = {"and": " AND ", "or": " OR ", "weighted": " + "}
        join = logic_map.get(rule.logic, " ? ")
        return f"{action}[{rule.logic}]: " + join.join(parts)

    # ---- 评估 ----

    def evaluate(self, data: pd.DataFrame, date: str = "",
                 symbol: str = "") -> Optional[Signal]:
        """
        在当前数据上评估所有规则，返回交易信号

        data: OHLCV DataFrame（完整历史到当前）
        """
        calc = FactorCalculator(data)

        # 评估买入规则
        for rule in self.buy_rules:
            if self._eval_rule(rule, calc):
                return Signal(
                    action="BUY", symbol=symbol, date=date,
                    price=data["close"].iloc[-1],
                    reason=f"[{self.name}] {rule.description or self.describe('BUY')}",
                )

        # 评估卖出规则
        for rule in self.sell_rules:
            if self._eval_rule(rule, calc):
                return Signal(
                    action="SELL", symbol=symbol, date=date,
                    price=data["close"].iloc[-1],
                    reason=f"[{self.name}] {rule.description or self.describe('SELL')}",
                )

        return None

    def _eval_rule(self, rule: SignalRule, calc: FactorCalculator) -> bool:
        """评估单条规则是否触发 (考虑IC衰减系数)"""
        if not rule.conditions:
            return False

        results = []
        weights = []

        for cond in rule.conditions:
            val = self._get_factor_value(cond.factor, calc)
            if val is None or np.isnan(val):
                results.append(False)
                weights.append(cond.weight * cond.decay_factor)
                continue

            ok = self._check_operator(val, cond.operator, cond.threshold, cond.threshold2)
            results.append(ok)
            # 权重乘以IC衰减系数: 衰减因子 > 禁用, 权重降低
            weights.append(cond.weight * cond.decay_factor)

        if rule.logic == "and":
            return all(results)
        elif rule.logic == "or":
            return any(results)
        elif rule.logic == "weighted":
            score = sum(w for r, w in zip(results, weights) if r)
            return score >= rule.threshold

        return False

    def apply_decay(self, factor_name: str, decay: float):
        """对指定因子的所有条件应用IC衰减系数

        decay: 0.0=禁用, 0.3=严重衰减, 0.5=轻度衰减, 1.0=正常
        """
        for rule in self.buy_rules + self.sell_rules:
            for cond in rule.conditions:
                if cond.factor == factor_name:
                    cond.decay_factor = decay

    def get_active_factors(self) -> List[str]:
        """获取当前所有非禁用因子"""
        active = set()
        for rule in self.buy_rules + self.sell_rules:
            for cond in rule.conditions:
                if cond.decay_factor > 0:
                    active.add(cond.factor)
        return sorted(active)

    def get_decaying_factors(self) -> Dict[str, float]:
        """获取所有衰减中的因子及其系数"""
        decaying = {}
        for rule in self.buy_rules + self.sell_rules:
            for cond in rule.conditions:
                if cond.decay_factor < 1.0:
                    decaying[cond.factor] = cond.decay_factor
        return decaying

    def _get_factor_value(self, factor: str, calc: FactorCalculator) -> Optional[float]:
        """获取最新因子值"""
        method_map = {
            "rsi_norm": calc.f_rsi,
            "ma_deviation": calc.f_ma_deviation,
            "ma_alignment": calc.f_ma_alignment,
            "ma_slope": calc.f_ma_slope,
            "trend_strength": calc.f_adx_like,
            "macd_hist": calc.f_macd_hist,
            "roc_10": calc.f_roc,
            "price_position": calc.f_price_position,
            "momentum_score": calc.f_momentum_score,
            "volatility": calc.f_volatility,
            "bollinger_pos": calc.f_bollinger_position,
            "bollinger_width": calc.f_bollinger_width,
            "atr_ratio": calc.f_atr_ratio,
            "volume_ratio": calc.f_volume_ratio,
            "volume_trend": calc.f_volume_trend,
            "obv_divergence": calc.f_obv_divergence,
            "hammer": calc.f_hammer,
            "engulfing": calc.f_engulfing,
        }
        if factor not in method_map:
            return None
        try:
            series = method_map[factor]()
            return series.iloc[-1]
        except (IndexError, TypeError):
            return None

    @staticmethod
    def _check_operator(val: float, op: str, t1: float, t2: float = None) -> bool:
        if op == "gt":
            return val > t1
        elif op == "lt":
            return val < t1
        elif op == "between" and t2 is not None:
            return t1 <= val <= t2
        # cross 类需要历史值，这里简化处理
        elif op == "cross_above":
            return val > t1
        elif op == "cross_below":
            return val < t1
        return False

    # ---- 内部 ----

    def _get_rule(self, action: str) -> Optional[SignalRule]:
        rules = self.buy_rules if action == "BUY" else self.sell_rules
        if not rules:
            return None
        return rules[-1]

    def _get_or_create_rule(self, action: str) -> SignalRule:
        rules = self.buy_rules if action == "BUY" else self.sell_rules
        if not rules:
            rule = SignalRule(action=action)
            rules.append(rule)
            return rule
        return rules[-1]

    # ---- 从 StrategyConfig 构建 ----

    def to_strategy(self, config: StrategyConfig = None):
        """
        将组合器转换成一个可以直接传入 BacktestEngine.run() 的策略对象
        """
        composer = self

        class ComposedStrategy:
            def __init__(self, cfg=None):
                self.config = cfg or config or StrategyConfig(name=composer.name)

            def on_bar(self, i, data, portfolio):
                if i < 20:
                    return None
                symbol = self.config.name or "STOCK"
                date = str(data.iloc[-1].get("date", ""))[:10]
                has_position = symbol in portfolio.positions

                if not has_position:
                    return composer.evaluate(data, date, symbol)
                else:
                    # 检查卖出信号
                    for rule in composer.sell_rules:
                        calc = FactorCalculator(data)
                        if composer._eval_rule(rule, calc):
                            return Signal(
                                action="SELL", symbol=symbol, date=date,
                                price=data["close"].iloc[-1],
                                reason=f"[{composer.name}] {rule.description}",
                            )
                    return None

            def buy_signal(self, data):
                return False

            def sell_signal(self, data):
                return False

        return ComposedStrategy()


# ============================================================
# 预设策略模板（你的独有配方）
# ============================================================

def create_contrarian_v1():
    """逆势交易 V1: RSI超卖 + 布林下轨 + 放量确认"""
    return (SignalComposer("逆势交易V1")
        .rsi_oversold(14, 30, weight=3)
        .near_bollinger_low(weight=2)
        .volume_surge(1.3, weight=1)
        .set_logic("weighted", threshold=4.0, action="BUY")
        .near_bollinger_high(weight=2)
        .rsi_overbought(14, 70, weight=2)
        .set_logic("weighted", threshold=3.0, action="SELL")
    )


def create_trend_following_v1():
    """趋势跟踪 V1: 均线多头 + 趋势强 + 动量确认"""
    return (SignalComposer("趋势跟踪V1")
        .ma_golden_cross(10, 30, weight=3)
        .trend_strong(weight=2)
        .momentum_strong(weight=1)
        .set_logic("weighted", threshold=4.0, action="BUY")
        .ma_dead_cross(10, 30, weight=3)
        .trend_weak(weight=2)
        .set_logic("weighted", threshold=4.0, action="SELL")
    )


def create_volume_breakout_v1():
    """量价突破 V1: 放量 + 动量 + 趋势确认"""
    return (SignalComposer("量价突破V1")
        .volume_surge(2.0, weight=3)
        .momentum_strong(weight=2)
        .trend_strong(weight=1)
        .set_logic("weighted", threshold=4.0, action="BUY")
        .momentum_weak(weight=2)
        .set_logic("weighted", threshold=2.0, action="SELL")
    )


def create_mean_reversion_v2():
    """均值回归 V2: 偏离均线 + 低波动 + 锤子确认"""
    return (SignalComposer("均值回归V2")
        .price_below_ma(20, weight=2)
        .add_condition("volatility", "lt", 0.6, weight=1, action="BUY")
        .hammer_pattern(weight=2)
        .set_logic("weighted", threshold=3.0, action="BUY")
        .price_above_ma(20, weight=2)
        .set_logic("or", threshold=0, action="SELL")
    )


# 注册你的独有策略模板
PRESET_STRATEGIES = {
    "contrarian_v1": {
        "name": "逆势交易V1",
        "factory": create_contrarian_v1,
        "description": "RSI超卖+布林下轨+放量，逆势抄底",
    },
    "trend_following_v1": {
        "name": "趋势跟踪V1",
        "factory": create_trend_following_v1,
        "description": "均线多头+强趋势+动量确认，顺势而为",
    },
    "volume_breakout_v1": {
        "name": "量价突破V1",
        "factory": create_volume_breakout_v1,
        "description": "放量突破+动量+趋势三重确认",
    },
    "mean_reversion_v2": {
        "name": "均值回归V2",
        "factory": create_mean_reversion_v2,
        "description": "偏离均线+低波动+锤子线，精准抄底",
    },
}
