"""
StrategyEnsemble — 策略集成投票器 (v5.7)

1. 读取所有策略信号 (-1/0/1)
2. 加权投票 → 综合得分
3. 阈值触发买卖 (默认 ±0.6)
4. 动态权重: 基于滚动夏普自动调整
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


@dataclass
class StrategySignal:
    """单个策略在某日的信号"""
    strategy: str
    date: str
    signal: float    # -1(看空) / 0(中性) / 1(看多)
    confidence: float = 1.0


@dataclass
class StrategyWeight:
    """策略权重配置"""
    strategy: str
    weight: float          # 归一化权重 (0~1, 总和=1)
    sharpe_rolling: float = 0.0   # 滚动夏普 (用于动态调整)
    track_record: int = 0         # 累计正确次数


class StrategyEnsemble:
    """策略集成投票器"""

    def __init__(self,
                 weights: Dict[str, float] = None,
                 vote_threshold: float = 0.6,
                 dynamic_weight: bool = True,
                 rolling_window: int = 60,
                 learning_rate: float = 0.1):
        """
        weights:         {strategy_name: weight}  初始权重
        vote_threshold:  综合得分超此值触发信号 (建议0.4~0.6)
        dynamic_weight:  是否启用动态权重调整
        rolling_window:  滚动夏普计算窗口
        learning_rate:   权重调整速率 (0~1)
        """
        self.initial_weights = weights or {}
        self.vote_threshold = vote_threshold
        self.dynamic_weight = dynamic_weight
        self.rolling_window = rolling_window
        self.learning_rate = learning_rate

        # 权重状态
        self.weights: Dict[str, float] = dict(self.initial_weights) if self.initial_weights else {}

        # 信号历史
        self.signal_history: List[StrategySignal] = []

        # 策略跟踪记录
        self._returns: Dict[str, List[float]] = {}     # 每日 PnL
        self._correct: Dict[str, int] = {}              # 正确次数
        self._total: Dict[str, int] = {}                # 总次数

    # ═══════════════════════════════════════════
    # 1. 收集信号
    # ═══════════════════════════════════════════

    def add_signal(self, strategy: str, date: str, signal: float,
                   confidence: float = 1.0):
        """添加单个策略信号"""
        s = StrategySignal(strategy, date, signal, confidence)
        self.signal_history.append(s)

    def add_batch(self, signals: List[Tuple[str, str, float]]):
        """批量添加: [(strategy, date, signal), ...]"""
        for strat, date, sig in signals:
            self.add_signal(strat, date, sig)

    def get_signals_on(self, date: str) -> List[StrategySignal]:
        """获取某日所有策略信号"""
        return [s for s in self.signal_history if s.date == date]

    # ═══════════════════════════════════════════
    # 2. 加权投票
    # ═══════════════════════════════════════════

    def vote(self, date: str) -> Tuple[float, str, Dict]:
        """
        加权投票, 返回: (综合得分, 决策, 投票详情)
        """
        signals = self.get_signals_on(date)
        if not signals:
            return 0.0, "HOLD", {}

        # 确保所有权重存在
        active_strategies = set(s.strategy for s in signals)
        self._normalize_weights(active_strategies)

        total_score = 0.0
        total_weight = 0.0
        detail = {}

        for s in signals:
            w = self.weights.get(s.strategy, 1.0 / len(active_strategies))
            score = s.signal * w * s.confidence
            total_score += score
            total_weight += w
            detail[s.strategy] = {
                "signal": s.signal,
                "weight": round(w, 3),
                "score": round(score, 3),
            }

        # 归一化得分到 [-1, 1]
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0.0

        normalized_score = round(max(-1.0, min(1.0, normalized_score)), 3)

        # 决策
        if normalized_score >= self.vote_threshold:
            decision = "BUY"
        elif normalized_score <= -self.vote_threshold:
            decision = "SELL"
        else:
            decision = "HOLD"

        return normalized_score, decision, detail

    def _normalize_weights(self, active_strategies: set):
        """确保活跃策略的权重归一化"""
        # 给未配置权重的策略分配默认权重
        for s in active_strategies:
            if s not in self.weights:
                self.weights[s] = 1.0

        # 归一化
        total = sum(self.weights.get(s, 0) for s in active_strategies)
        if total > 0:
            for s in active_strategies:
                self.weights[s] = self.weights.get(s, 1.0) / total

    # ═══════════════════════════════════════════
    # 3. 动态权重调整
    # ═══════════════════════════════════════════

    def update_weights_from_sharpe(self, recent_performance: Dict[str, float]):
        """
        根据近期夏普调整权重
        recent_performance: {strategy: rolling_sharpe}

        算法: softmax → 高分策略获得更高权重
        """
        if not self.dynamic_weight or not recent_performance:
            return

        strategies = list(recent_performance.keys())
        sharpes = np.array([recent_performance[s] for s in strategies])

        # Softmax
        # 用温度参数控制分布尖锐度 (温度越低越集中在高分策略)
        temperature = 0.5
        exp_sharpes = np.exp(sharpes / max(temperature, 0.01))
        softmax_weights = exp_sharpes / exp_sharpes.sum()

        # 平滑更新 (EMA)
        for i, s in enumerate(strategies):
            old_w = self.weights.get(s, 1.0 / len(strategies))
            new_w = softmax_weights[i]
            self.weights[s] = old_w * (1 - self.learning_rate) + new_w * self.learning_rate

        # 归一化
        total = sum(self.weights.values())
        if total > 0:
            for s in self.weights:
                self.weights[s] /= total

    def update_from_pnl(self, strategy: str, pnl: float):
        """根据单笔盈亏更新跟踪记录"""
        if strategy not in self._returns:
            self._returns[strategy] = []
            self._correct[strategy] = 0
            self._total[strategy] = 0

        self._returns[strategy].append(pnl)
        self._total[strategy] += 1
        if pnl > 0:
            self._correct[strategy] += 1

        # 每轮更新滚动夏普
        if len(self._returns[strategy]) >= self.rolling_window:
            recent = self._returns[strategy][-self.rolling_window:]
            mean_ret = np.mean(recent)
            std_ret = np.std(recent)
            if std_ret > 0:
                sharpe = mean_ret / std_ret * np.sqrt(252)
                # 更新单策略权重
                self._adjust_single_weight(strategy, sharpe)

    def _adjust_single_weight(self, strategy: str, sharpe: float):
        """根据夏普调整单个策略权重"""
        if not self.dynamic_weight:
            return
        # 夏普 > 0 增权, < 0 减权
        factor = 1.0 + self.learning_rate * np.sign(sharpe) * min(abs(sharpe), 2.0)
        self.weights[strategy] = self.weights.get(strategy, 0.1) * factor
        # 归一化
        total = sum(self.weights.values())
        if total > 0:
            for s in self.weights:
                self.weights[s] /= total

    # ═══════════════════════════════════════════
    # 4. 报告
    # ═══════════════════════════════════════════

    def get_weights(self) -> Dict[str, float]:
        """当前权重"""
        return {k: round(v, 4) for k, v in sorted(self.weights.items(), key=lambda x: -x[1])}

    def get_track_record(self) -> pd.DataFrame:
        """策略跟踪记录"""
        rows = []
        for s in self.weights:
            total = self._total.get(s, 0)
            correct = self._correct.get(s, 0)
            wr = correct / total * 100 if total > 0 else 0
            rows.append({
                "策略": s,
                "权重": round(self.weights.get(s, 0), 3),
                "总信号": total,
                "正确": correct,
                "准确率(%)": round(wr, 1),
            })
        return pd.DataFrame(rows).sort_values("权重", ascending=False)

    def report(self) -> str:
        """打印集成状态"""
        df = self.get_track_record()
        lines = ["═══ Strategy Ensemble ═══"]
        lines.append(f"阈值: ±{self.vote_threshold} | 动态权重: {self.dynamic_weight}")
        lines.append(f"策略数: {len(self.weights)}")
        lines.append("")
        lines.append(df.to_string(index=False))
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 便捷函数: 从现有策略库自动生成集成器
# ═══════════════════════════════════════════════════════════

DEFAULT_WEIGHTS = {
    "ma_cross": 0.15,
    "rsi": 0.15,
    "macd": 0.10,
    "bollinger": 0.10,
    "momentum": 0.15,
    "mean_reversion": 0.10,
    "turtle": 0.10,
    "contrarian_v1": 0.05,
    "trend_following_v1": 0.05,
    "volume_breakout_v1": 0.05,
}


def create_ensemble(weights: Dict[str, float] = None,
                    threshold: float = 0.5,
                    dynamic: bool = True) -> StrategyEnsemble:
    """快速创建集成器"""
    w = weights or DEFAULT_WEIGHTS
    return StrategyEnsemble(weights=w, vote_threshold=threshold, dynamic_weight=dynamic)


class EnsembleStrategy:
    """集成策略适配器 — 兼容 BacktestEngine"""

    def __init__(self, symbol: str, threshold: float = 0.5, user_id: int = None):
        self.symbol = symbol
        self.user_id = user_id
        self.ensemble = create_ensemble(threshold=threshold, dynamic=True)
        self.config = type('obj', (object,), {'name': symbol})()

    def on_bar(self, i: int, data: pd.DataFrame, portfolio) -> Optional[object]:
        if i < 60:
            return None
        from src.models.strategy import Signal
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES

        date = str(data.iloc[-1].get("date", ""))[:10]
        symbol = self.symbol
        current_price = data["close"].iloc[-1]
        all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())

        # 收集各策略信号
        has_position = symbol in portfolio.positions
        for key in all_s:
            if key == "ensemble":
                continue
            try:
                s = _make_strategy_instance(key, {}, symbol)
                sig = s.on_bar(i, data, portfolio)
                if sig is not None:
                    val = 1 if sig.action == "BUY" else (-1 if sig.action == "SELL" else 0)
                    self.ensemble.add_signal(key, date, val)
            except:
                pass

        score, decision, _ = self.ensemble.vote(date)

        if not has_position and decision == "BUY":
            return Signal(action="BUY", symbol=symbol, date=date,
                          price=current_price, reason=f"集成投票({score:.2f})")
        if has_position and decision == "SELL":
            return Signal(action="SELL", symbol=symbol, date=date,
                          price=current_price, reason=f"集成投票({score:.2f})")

        return None


def run_ensemble_backtest(symbol: str, start_date: str = "2024-01-01",
                          ensemble: StrategyEnsemble = None):
    """
    对单只股票运行集成回测
    返回: DataFrame (date, 综合得分, 决策, 各策略信号)
    """
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine
    from src.backtest.batch_runner import _make_strategy_instance
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES

    if ensemble is None:
        ensemble = create_ensemble()

    data = get_data(symbol, "A股", start_date=start_date)
    if data is None or len(data) == 0:
        return None

    all_strategies = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())

    # 运行每个策略, 收集信号
    strategy_signals = {}
    for key in all_strategies:
        try:
            s = _make_strategy_instance(key, {}, symbol)
            r = BacktestEngine().run(s, data)
            # 提取买卖信号
            for t in r["portfolio"].trade_log:
                date = t["date"][:10]
                if date not in strategy_signals:
                    strategy_signals[date] = {}
                if t["action"] == "BUY":
                    strategy_signals[date][key] = 1
                elif t["action"] == "SELL":
                    strategy_signals[date][key] = -1
        except Exception:
            pass

    # 投票
    dates = sorted(strategy_signals.keys())
    results = []
    for date in dates:
        for key, sig in strategy_signals[date].items():
            ensemble.add_signal(key, date, sig)
        score, decision, detail = ensemble.vote(date)
        results.append({
            "date": date,
            "score": score,
            "decision": decision,
            "detail": detail,
        })

    return pd.DataFrame(results)
