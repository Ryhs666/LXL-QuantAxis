"""
策略优化引擎 — 参数扫描、网格搜索、Walk-Forward 分析

功能:
  - Grid Search: 遍历参数组合，按指定指标排名
  - Walk-Forward: 样本外检验，避免过拟合
  - 基准对比: vs 沪深300 / 买入持有
  - 结果持久化: 保存/加载优化结果
"""

import sys
import os
import json
import time
from datetime import datetime
from itertools import product
from typing import Optional, List, Dict, Callable

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.backtest.engine import BacktestEngine
from src.backtest.data_feed import get_data
from src.strategies.library import STRATEGIES, get_strategy_class
from src.models.strategy import StrategyConfig


# ============================================================
# 优化指标
# ============================================================

def rank_by_sharpe(metrics: dict) -> float:
    """按夏普比率排名（越高越好）"""
    return metrics.get("夏普比率", 0)

def rank_by_total_return(metrics: dict) -> float:
    """按总收益率排名"""
    ret_str = metrics.get("总收益率", "+0.00%")
    return float(ret_str.replace("%", "").replace("+", ""))

def rank_by_calmar(metrics: dict) -> float:
    """按卡尔玛比率排名"""
    val = metrics.get("卡尔玛比率", 0)
    return val if val != float("inf") else 999

def rank_by_win_rate(metrics: dict) -> float:
    """按胜率排名"""
    wr = metrics.get("胜率", "0.0%")
    return float(wr.replace("%", ""))

def rank_by_profit_factor(metrics: dict) -> float:
    """按盈利因子排名"""
    pf = metrics.get("盈利因子", "0.00")
    return float(pf) if pf != "∞" else 999

# 复合评分：收益率 * 夏普 * 胜率 的标准化乘积
def rank_composite(metrics: dict) -> float:
    ret = rank_by_total_return(metrics)
    sharpe = max(rank_by_sharpe(metrics), 0.01)
    win_rate = max(rank_by_win_rate(metrics), 1)
    return ret * sharpe * win_rate / 100


RANK_FUNCTIONS = {
    "sharpe": ("夏普比率", rank_by_sharpe),
    "return": ("总收益率", rank_by_total_return),
    "calmar": ("卡尔玛比率", rank_by_calmar),
    "win_rate": ("胜率", rank_by_win_rate),
    "profit_factor": ("盈利因子", rank_by_profit_factor),
    "composite": ("综合评分", rank_composite),
}


# ============================================================
# Grid Search
# ============================================================

class GridSearch:
    """网格搜索参数优化"""

    def __init__(self, symbol: str, market: str = "A股",
                 start_date: str = "2020-01-01",
                 end_date: str = None,
                 initial_capital: float = 100_000,
                 commission_rate: float = 0.0003,
                 rank_by: str = "sharpe"):
        self.symbol = symbol
        self.market = market
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.rank_func = RANK_FUNCTIONS.get(rank_by, RANK_FUNCTIONS["sharpe"])
        self.results = []

    def run(self, strategy_name: str,
            param_grid: Dict[str, list],
            position_size_pct: float = 0.3,
            verbose: bool = True) -> pd.DataFrame:
        """
        执行网格搜索

        参数:
            strategy_name: 策略名 (如 "ma_cross")
            param_grid: 参数网格，如 {"fast_period": [5,10,20], "slow_period": [20,30,40]}
            position_size_pct: 仓位比例
            verbose: 是否打印进度

        返回:
            排序后的结果 DataFrame
        """
        strategy_cls = get_strategy_class(strategy_name)
        strategy_info = STRATEGIES.get(strategy_name, {})

        # 加载数据
        if verbose:
            print(f"\n{'='*60}")
            print(f"  网格搜索: {strategy_info.get('name', strategy_name)}")
            print(f"  标的: {self.market} {self.symbol}")
            print(f"  时间: {self.start_date} ~ {self.end_date or '今天'}")
            print(f"  排名指标: {self.rank_func[0]}")
            print(f"{'='*60}")

        data = get_data(self.symbol, self.market,
                        start_date=self.start_date, end_date=self.end_date)

        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))

        total = len(combinations)
        if verbose:
            print(f"\n  共 {total} 种参数组合")

        self.results = []
        start_time = time.time()

        for idx, values in enumerate(combinations):
            params = dict(zip(param_names, values))

            # 构建策略
            config = StrategyConfig(
                name=self.symbol,
                initial_capital=self.initial_capital,
                position_size_pct=position_size_pct,
                commission_rate=self.commission_rate,
            )

            try:
                strategy = strategy_cls(config=config, **params)
                engine = BacktestEngine(
                    initial_capital=self.initial_capital,
                    commission_rate=self.commission_rate,
                )
                result = engine.run(strategy, data, position_size_pct=position_size_pct)
                metrics = result["metrics"]

                score = self.rank_func[1](metrics)

                record = {
                    **params,
                    "score": round(score, 4),
                    "total_return": metrics.get("总收益率", "N/A"),
                    "sharpe": metrics.get("夏普比率", 0),
                    "max_drawdown": metrics.get("最大回撤", "N/A"),
                    "win_rate": metrics.get("胜率", "N/A"),
                    "profit_factor": metrics.get("盈利因子", "N/A"),
                    "calmar": metrics.get("卡尔玛比率", 0),
                    "trade_count": metrics.get("交易次数", 0),
                }
                self.results.append(record)

            except Exception as e:
                if verbose:
                    print(f"    [{idx+1}/{total}] {params} ERROR: {e}")
                continue

            if verbose and (idx + 1) % max(1, total // 10) == 0:
                elapsed = time.time() - start_time
                eta = (elapsed / (idx + 1)) * (total - idx - 1)
                print(f"    [{idx+1}/{total}] 已耗时 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

        df = pd.DataFrame(self.results)
        if not df.empty:
            df = df.sort_values("score", ascending=False).reset_index(drop=True)

        if verbose and not df.empty:
            elapsed = time.time() - start_time
            print(f"\n  ✅ 搜索完成！耗时 {elapsed:.1f}s")
            print(f"\n  🏆 Top 5 参数组合：")
            print(df.head(5).to_string())

        return df

    def best_params(self) -> dict:
        """返回最优参数"""
        if not self.results:
            return {}
        return max(self.results, key=lambda r: r["score"])


# ============================================================
# Walk-Forward Analysis
# ============================================================

class WalkForward:
    """
    Walk-Forward 分析

    将数据分成多个时间段:
      1. 在训练期做参数优化
      2. 用最优参数在测试期跑回测
      3. 滚动窗口，收集所有测试期结果
      4. 汇总 = 样本外真实表现
    """

    def __init__(self, symbol: str, market: str = "A股",
                 initial_capital: float = 100_000):
        self.symbol = symbol
        self.market = market
        self.initial_capital = initial_capital

    def run(self, strategy_name: str, param_grid: dict,
            train_years: int = 3, test_months: int = 6,
            start_date: str = "2018-01-01",
            rank_by: str = "sharpe",
            verbose: bool = True) -> dict:
        """
        执行 Walk-Forward 分析

        参数:
            strategy_name: 策略名
            param_grid: 参数网格
            train_years: 训练期年数
            test_months: 测试期月数
            start_date: 整体起始日期
            rank_by: 优化指标
        """
        data = get_data(self.symbol, self.market, start_date=start_date)
        data["date"] = pd.to_datetime(data["date"])

        overall_start = data["date"].min()
        overall_end = data["date"].max()

        if verbose:
            print(f"\n{'='*60}")
            print(f"  Walk-Forward 分析: {strategy_name}")
            print(f"  标的: {self.market} {self.symbol}")
            print(f"  训练期: {train_years}年 | 测试期: {test_months}月")
            print(f"{'='*60}")

        windows = []
        train_start = overall_start
        test_end_cursor = train_start + pd.DateOffset(years=train_years) + pd.DateOffset(months=test_months)

        while test_end_cursor <= overall_end:
            train_end = train_start + pd.DateOffset(years=train_years)
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=test_months)

            windows.append({
                "train_start": str(train_start.date()),
                "train_end": str(train_end.date()),
                "test_start": str(test_start.date()),
                "test_end": str(test_end.date()),
            })

            train_start = train_end + pd.DateOffset(months=test_months)
            test_end_cursor = train_start + pd.DateOffset(years=train_years) + pd.DateOffset(months=test_months)

        if verbose:
            print(f"\n  共 {len(windows)} 个窗口")

        all_test_trades = []
        all_test_metrics = []
        window_results = []

        for wi, w in enumerate(windows):
            if verbose:
                print(f"\n  --- 窗口 {wi+1}/{len(windows)} ---")
                print(f"  训练: {w['train_start']} ~ {w['train_end']}")
                print(f"  测试: {w['test_start']} ~ {w['test_end']}")

            # 训练期：网格搜索
            gs = GridSearch(
                self.symbol, self.market,
                start_date=w["train_start"],
                end_date=w["train_end"],
                initial_capital=self.initial_capital,
                rank_by=rank_by,
            )
            df_results = gs.run(strategy_name, param_grid, verbose=False)

            if df_results.empty:
                if verbose:
                    print(f"  ⚠️ 训练期无有效结果，跳过")
                continue

            best = df_results.iloc[0].to_dict()
            if verbose:
                print(f"  最优参数: { {k: v for k, v in best.items() if k in param_grid} }")

            # 测试期：用最优参数跑回测
            strategy_cls = get_strategy_class(strategy_name)
            best_kwargs = {k: v for k, v in best.items() if k in param_grid}

            param_type_map = {}
            for k in param_grid:
                if param_grid[k] and isinstance(param_grid[k][0], int):
                    param_type_map[k] = int
                elif param_grid[k] and isinstance(param_grid[k][0], float):
                    param_type_map[k] = float
                elif param_grid[k] and isinstance(param_grid[k][0], bool):
                    param_type_map[k] = bool

            for k, t in param_type_map.items():
                if k in best_kwargs:
                    try:
                        best_kwargs[k] = t(best_kwargs[k])
                    except (ValueError, TypeError):
                        pass

            test_data = get_data(self.symbol, self.market,
                                 start_date=w["test_start"],
                                 end_date=w["test_end"])

            if len(test_data) < 20:
                continue

            config = StrategyConfig(
                name=self.symbol,
                initial_capital=self.initial_capital,
                commission_rate=0.0003,
            )

            try:
                strategy = strategy_cls(config=config, **best_kwargs)
                engine = BacktestEngine(initial_capital=self.initial_capital)
                result = engine.run(strategy, test_data)

                test_metrics = result["metrics"]
                test_trades = result["portfolio"].trade_log

                all_test_metrics.append(test_metrics)
                all_test_trades.extend(test_trades)

                window_results.append({
                    "window": wi + 1,
                    "train": f"{w['train_start']}~{w['train_end']}",
                    "test": f"{w['test_start']}~{w['test_end']}",
                    "best_params": best_kwargs,
                    "test_return": test_metrics.get("总收益率", "N/A"),
                    "test_sharpe": test_metrics.get("夏普比率", 0),
                    "test_win_rate": test_metrics.get("胜率", "N/A"),
                    "test_trades": test_metrics.get("交易次数", 0),
                })

                if verbose:
                    print(f"  测试结果: 收益率={test_metrics.get('总收益率', 'N/A')}, "
                          f"胜率={test_metrics.get('胜率', 'N/A')}, "
                          f"交易={test_metrics.get('交易次数', 0)}笔")

            except Exception as e:
                if verbose:
                    print(f"  ❌ 测试期回测失败: {e}")

        # 汇总
        summary = self._summarize(all_test_metrics, window_results)

        if verbose:
            print(f"\n{'='*60}")
            print(f"  Walk-Forward 汇总")
            print(f"{'='*60}")
            for k, v in summary.items():
                print(f"  {k}: {v}")

        return {
            "windows": window_results,
            "summary": summary,
            "all_test_metrics": all_test_metrics,
            "all_test_trades": all_test_trades,
        }

    def _summarize(self, all_metrics: list, window_results: list) -> dict:
        if not all_metrics:
            return {"状态": "无有效结果"}

        # 逐窗口汇总
        returns_str = [m.get("总收益率", "+0.00%") for m in all_metrics]
        returns = []
        for r in returns_str:
            try:
                returns.append(float(r.replace("%", "").replace("+", "")))
            except ValueError:
                returns.append(0)

        sharpe_vals = [m.get("夏普比率", 0) for m in all_metrics]
        win_rates_str = [m.get("胜率", "0.0%") for m in all_metrics]
        win_rates = []
        for w in win_rates_str:
            try:
                win_rates.append(float(w.replace("%", "")))
            except ValueError:
                win_rates.append(0)

        trade_counts = [m.get("交易次数", 0) for m in all_metrics]

        # 如果 we combine all test periods:
        profitable_windows = sum(1 for r in returns if r > 0)

        return {
            "窗口总数": len(window_results),
            "盈利窗口数": profitable_windows,
            "窗口胜率": f"{profitable_windows / len(window_results) * 100:.1f}%" if window_results else "N/A",
            "平均窗口收益率": f"{np.mean(returns):+.2f}%",
            "中位窗口收益率": f"{np.median(returns):+.2f}%",
            "最佳窗口": f"{max(returns):+.2f}%",
            "最差窗口": f"{min(returns):+.2f}%",
            "平均夏普": f"{np.mean(sharpe_vals):.2f}",
            "平均胜率": f"{np.mean(win_rates):.1f}%",
            "总交易数": sum(trade_counts),
        }


# ============================================================
# 基准对比
# ============================================================

def benchmark_compare(symbol: str, market: str = "A股",
                      benchmark_symbol: str = "000300",
                      start_date: str = "2020-01-01",
                      end_date: str = None,
                      initial_capital: float = 100_000) -> pd.DataFrame:
    """
    对比策略 vs 基准（沪深300） vs 买入持有

    返回: DataFrame 包含三者的净值曲线
    """
    from src.backtest.data_feed import get_data as gd

    # 股票数据
    stock_data = gd(symbol, market, start_date, end_date)

    # 基准指数
    try:
        benchmark_data = gd(benchmark_symbol, "指数", start_date, end_date)
        has_benchmark = True
    except Exception:
        has_benchmark = False

    # 买入持有策略的净值
    stock_data = stock_data.copy()
    if len(stock_data) > 0:
        first_close = stock_data["close"].iloc[0]
        stock_data["buy_hold_value"] = stock_data["close"] / first_close * initial_capital
        stock_data["buy_hold_return"] = (stock_data["close"] / first_close - 1) * 100

    # 基准净值
    if has_benchmark and len(benchmark_data) > 0:
        benchmark_data = benchmark_data.copy()
        bm_first = benchmark_data["close"].iloc[0]
        benchmark_data["benchmark_value"] = benchmark_data["close"] / bm_first * initial_capital

    return {
        "stock": stock_data,
        "benchmark": benchmark_data if has_benchmark else None,
        "start_date": start_date,
        "end_date": end_date,
    }


def print_benchmark_report(strategy_result: dict, symbol: str,
                           market: str = "A股",
                           benchmark_symbol: str = "000300",
                           start_date: str = "2020-01-01",
                           end_date: str = None):
    """打印基准对比报告"""
    metrics = strategy_result.get("metrics", {})
    comparison = benchmark_compare(symbol, market, benchmark_symbol,
                                   start_date, end_date)

    print("\n" + "=" * 60)
    print("  📊 基准对比报告")
    print("=" * 60)

    # 策略表现
    print("\n  【策略表现】")
    strat_return = metrics.get("总收益率", "N/A")
    print(f"    总收益率: {strat_return}")
    print(f"    夏普比率: {metrics.get('夏普比率', 'N/A')}")
    print(f"    最大回撤: {metrics.get('最大回撤', 'N/A')}")
    print(f"    胜率: {metrics.get('胜率', 'N/A')}")

    # 买入持有
    stock = comparison.get("stock")
    if stock is not None and len(stock) > 0:
        bh_return = stock["buy_hold_return"].iloc[-1]
        print("\n  【买入持有】")
        print(f"    总收益率: {bh_return:+.2f}%")

        try:
            bh_peak = stock["buy_hold_value"].cummax()
            bh_dd = (stock["buy_hold_value"] - bh_peak) / bh_peak * 100
            print(f"    最大回撤: {bh_dd.min():.2f}%")
        except Exception:
            pass

    # 基准
    benchmark = comparison.get("benchmark")
    if benchmark is not None and len(benchmark) > 0:
        bm_return = (benchmark["close"].iloc[-1] / benchmark["close"].iloc[0] - 1) * 100
        print(f"\n  【基准 ({benchmark_symbol})】")
        print(f"    总收益率: {bm_return:+.2f}%")

        try:
            bm_peak = benchmark["benchmark_value"].cummax()
            bm_dd = (benchmark["benchmark_value"] - bm_peak) / bm_peak * 100
            print(f"    最大回撤: {bm_dd.min():.2f}%")
        except Exception:
            pass

    # 胜负
    print("\n  【对比结论】")
    try:
        s_ret = float(strat_return.replace("%", "").replace("+", ""))
        if s_ret > bh_return:
            print(f"    ✅ 策略跑赢买入持有: {s_ret - bh_return:+.1f}%")
        else:
            print(f"    ❌ 策略跑输买入持有: {s_ret - bh_return:+.1f}%")
    except Exception:
        pass

    print()


# ============================================================
# 便捷函数
# ============================================================

def quick_optimize(symbol: str, strategy: str = "ma_cross",
                   start_date: str = "2020-01-01",
                   rank_by: str = "sharpe") -> pd.DataFrame:
    """一键优化：用默认参数范围做网格搜索"""
    from src.strategies.library import STRATEGIES

    if strategy not in STRATEGIES:
        raise ValueError(f"未知策略: {strategy}，可选: {list(STRATEGIES.keys())}")

    info = STRATEGIES[strategy]
    param_ranges = info.get("params", {})

    # 将 (low, high) 的 range 展开为离散值
    param_grid = {}
    for k, v in param_ranges.items():
        if isinstance(v, tuple):
            low, high = v
            if k.endswith("pct") or k.endswith("deviation"):
                param_grid[k] = np.linspace(low, high, 4).tolist()
            else:
                step = max(1, (high - low) // 4)
                param_grid[k] = list(range(low, high + 1, step))
        elif isinstance(v, list):
            param_grid[k] = v
        else:
            param_grid[k] = [v]

    gs = GridSearch(symbol, "A股", start_date=start_date, rank_by=rank_by)
    return gs.run(strategy, param_grid)


def quick_walkforward(symbol: str, strategy: str = "ma_cross",
                      start_date: str = "2018-01-01",
                      rank_by: str = "sharpe") -> dict:
    """一键 Walk-Forward"""
    from src.strategies.library import STRATEGIES

    info = STRATEGIES[strategy]
    param_ranges = info.get("params", {})

    param_grid = {}
    for k, v in param_ranges.items():
        if isinstance(v, tuple):
            low, high = v
            if k.endswith("pct") or k.endswith("deviation"):
                param_grid[k] = np.linspace(low, high, 3).tolist()
            else:
                step = max(1, (high - low) // 3)
                param_grid[k] = list(range(low, high + 1, step))
        elif isinstance(v, list):
            param_grid[k] = v
        else:
            param_grid[k] = [v]

    wf = WalkForward(symbol, "A股")
    return wf.run(strategy, param_grid, start_date=start_date, rank_by=rank_by)
