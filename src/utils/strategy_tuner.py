# -*- coding: utf-8 -*-
"""
Strategy Tuner — 策略参数贝叶斯/随机优化器

Optuna 贝叶斯优化 (优先) → 随机搜索 (回退)。

集成方式:
    python main.py --tune ma_cross              # CLI 一键调优
    python main.py --tune ma_cross --trials 100  # 自定义尝试次数
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Callable, Dict, Any, List, Tuple, Optional
from copy import deepcopy
import logging

logger = logging.getLogger("utils.strategy_tuner")

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


# ═══════════════════════════════════════════
# 默认目标函数
# ═══════════════════════════════════════════

def default_objective(backtest_result: Dict[str, Any]) -> float:
    """从回测结果提取优化目标 (最大化夏普)"""
    metrics = backtest_result.get("metrics", backtest_result)
    sharpe_str = metrics.get("夏普比率", metrics.get("sharpe", 0))
    try:
        return float(str(sharpe_str))
    except (ValueError, TypeError):
        pass

    returns = backtest_result.get("returns")
    if returns is not None and len(returns) > 0:
        excess = np.array(returns) - 0.03 / 252
        std = np.std(excess)
        if std > 0:
            return float(np.mean(excess) / std * np.sqrt(252))
    return 0.0


# ═══════════════════════════════════════════
# 参数空间 — 从 config 读取
# ═══════════════════════════════════════════

DEFAULT_PARAM_SPACE = {
    "ma_cross": {
        "fast_period": (3, 30, "int"),
        "slow_period": (10, 60, "int"),
    },
    "rsi": {
        "rsi_period": (7, 21, "int"),
        "oversold": (20, 40, "int"),
        "overbought": (60, 80, "int"),
    },
    "macd": {
        "fast": (8, 20, "int"),
        "slow": (20, 40, "int"),
        "signal": (5, 15, "int"),
    },
    "bollinger": {
        "period": (10, 40, "int"),
        "std_dev": (1.5, 3.0, "float"),
    },
    "turtle": {
        "entry_period": (10, 55, "int"),
        "exit_period": (5, 30, "int"),
        "atr_stop": (1.0, 3.0, "float"),
    },
}

PARAM_SPACE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config", "best_params.json",
)


# ═══════════════════════════════════════════
# StrategyTuner
# ═══════════════════════════════════════════

class StrategyTuner:
    """策略参数调优器"""

    def __init__(
        self,
        backtest_func: Callable[..., Dict[str, Any]],
        param_space: Dict[str, Tuple],
        objective_func: Callable = None,
        direction: str = "maximize",
        n_trials: int = 50,
    ):
        self.backtest_func = backtest_func
        self.param_space = param_space
        self.objective_func = objective_func or default_objective
        self.direction = direction
        self.n_trials = n_trials
        self.best_params = None
        self.best_score = -np.inf if direction == "maximize" else np.inf
        self.history = []

    def _suggest_params(self, trial) -> dict:
        params = {}
        for name, spec in self.param_space.items():
            if len(spec) >= 3:
                low, high, ptype = spec[0], spec[1], spec[2]
                if ptype == "int":
                    params[name] = trial.suggest_int(name, int(low), int(high))
                elif ptype == "float":
                    params[name] = trial.suggest_float(name, float(low), float(high))
                elif ptype == "categorical":
                    params[name] = trial.suggest_categorical(name, low)
                else:
                    params[name] = trial.suggest_float(name, float(low), float(high))
            else:
                params[name] = trial.suggest_float(name, float(spec[0]), float(spec[1]))
        return params

    def _random_params(self) -> dict:
        params = {}
        for name, spec in self.param_space.items():
            if len(spec) >= 3:
                low, high, ptype = spec[0], spec[1], spec[2]
                if ptype == "int":
                    params[name] = np.random.randint(int(low), int(high) + 1)
                elif ptype == "float":
                    params[name] = np.random.uniform(float(low), float(high))
                elif ptype == "categorical":
                    params[name] = np.random.choice(low)
            else:
                params[name] = np.random.uniform(float(spec[0]), float(spec[1]))
        return params

    def _evaluate(self, params: dict) -> float:
        try:
            result = self.backtest_func(**params)
            score = self.objective_func(result)
            self.history.append({"params": deepcopy(params), "score": score})
            return score
        except Exception as e:
            logger.error(f"参数 {params} 回测失败: {e}")
            return -np.inf if self.direction == "maximize" else np.inf

    def tune(self) -> dict:
        logger.info(f"开始调优: direction={self.direction}, trials={self.n_trials}")

        if HAS_OPTUNA and self.n_trials > 5:
            def objective(trial):
                return self._evaluate(self._suggest_params(trial))

            study = optuna.create_study(direction=self.direction)
            study.optimize(
                objective, n_trials=self.n_trials,
                show_progress_bar=False,
            )
            self.best_params = study.best_params
            self.best_score = study.best_value
        else:
            for i in range(self.n_trials):
                params = self._random_params()
                score = self._evaluate(params)
                if (self.direction == "maximize" and score > self.best_score) or \
                   (self.direction == "minimize" and score < self.best_score):
                    self.best_score = score
                    self.best_params = params
                if (i + 1) % 10 == 0:
                    print(f"  [Tuner] {i+1}/{self.n_trials} (best={self.best_score:.3f})")

        print(f"  [Tuner] 完成: {self.n_trials} 次, "
              f"best_score={self.best_score:.3f}, "
              f"best_params={self.best_params}")
        return self.best_params

    def save_best(self, path: str = None) -> str:
        path = path or PARAM_SPACE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "best_params": self.best_params,
                "best_score": self.best_score,
                "n_trials": self.n_trials,
                "history": [
                    {"params": h["params"], "score": h["score"]}
                    for h in sorted(self.history, key=lambda x: x["score"], reverse=True)[:20]
                ],
            }, f, indent=2, ensure_ascii=False)
        print(f"  [Tuner] 最佳参数已保存: {path}")
        return path


# ═══════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════

def run_tune_cli(
    strategy_key: str,
    symbol: str = "601398",
    start_date: str = "2024-01-01",
    n_trials: int = 50,
    save: bool = True,
):
    """CLI --tune 命令入口"""
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine
    from src.backtest.batch_runner import _make_strategy_instance

    param_space = DEFAULT_PARAM_SPACE.get(strategy_key)
    if not param_space:
        print(f"  未知策略: {strategy_key}, 可用: {list(DEFAULT_PARAM_SPACE)}")
        return None

    print(f"\n  [Tuner] 策略: {strategy_key}, 标的: {symbol}, "
          f"日期: {start_date}, 尝试: {n_trials}")

    data = get_data(symbol, "A股", start_date=start_date)
    if data is None or len(data) < 60:
        print(f"  数据不足")
        return None

    def run_backtest(**params):
        strategy = _make_strategy_instance(strategy_key, params, symbol)
        result = BacktestEngine().run(strategy, data)
        return result

    tuner = StrategyTuner(
        backtest_func=run_backtest,
        param_space=param_space,
        n_trials=n_trials,
    )
    best = tuner.tune()

    if save and best:
        tuner.save_best()

    return best
