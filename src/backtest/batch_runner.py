"""
批量回测引擎 + 结果数据库

核心功能:
  - 批量运行: N个策略 × M个标的
  - 结果持久化到 SQLite
  - 排名/对比/筛选
  - 增量运行（跳过已有结果）
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Optional, List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
import sqlite3

from src.backtest.engine import BacktestEngine
from src.backtest.data_feed import get_data
from src.strategies.library import STRATEGIES, get_strategy_class, MACrossStrategy, RSIStrategy
from src.strategies.library import MACDStrategy, BollingerStrategy, TurtleStrategy
from src.strategies.library import MomentumStrategy, MeanReversionStrategy
from src.factors.composer import PRESET_STRATEGIES
from src.models.strategy import StrategyConfig
from src.config import config
from src.utils import ProgressBar, Timer, safe_call, logger


# ============================================================
# 结果数据库
# ============================================================

class ResultDB:
    """回测结果 SQLite 存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(config.data_dir, "backtest_results.db")
        self.db_path = db_path
        self._ensure_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id        TEXT NOT NULL,
                    symbol        TEXT NOT NULL,
                    market        TEXT NOT NULL,
                    strategy      TEXT NOT NULL,
                    params_json   TEXT DEFAULT '{}',
                    start_date    TEXT NOT NULL,
                    end_date      TEXT NOT NULL,

                    -- 核心指标
                    total_return  REAL,
                    annual_return REAL,
                    sharpe        REAL,
                    max_drawdown  REAL,
                    calmar        REAL,
                    win_rate      REAL,
                    profit_factor REAL,
                    trade_count   INTEGER,
                    win_count     INTEGER,
                    loss_count    INTEGER,
                    avg_win       REAL,
                    avg_loss      REAL,

                    -- 上下文
                    initial_capital REAL,
                    final_equity  REAL,
                    run_time_sec  REAL,
                    error_msg     TEXT,
                    created_at    TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_strategy ON backtest_runs(strategy)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_symbol ON backtest_runs(symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_sharpe ON backtest_runs(sharpe DESC)
            """)

    def _safe_float(self, val, default=0.0) -> float:
        """安全转换为 float，处理 ∞/N/A 等特殊值"""
        try:
            v = float(val)
            if np.isinf(v) or np.isnan(v):
                return default
            return v
        except (ValueError, TypeError):
            try:
                s = str(val).replace("%", "").replace("¥", "").replace("+", "").replace(",", "")
                if s in ("∞", "inf", "-inf", "N/A", ""):
                    return default
                return float(s)
            except (ValueError, TypeError):
                return default

    def _safe_int(self, val, default=0) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def save_result(self, run_id: str, symbol: str, market: str,
                    strategy: str, params: dict,
                    start_date: str, end_date: str,
                    metrics: dict, run_time: float,
                    error: str = None):
        sf = self._safe_float
        si = self._safe_int

        with self._get_conn() as conn:
            conn.execute("DELETE FROM backtest_runs WHERE run_id = ?", (run_id,))
            conn.execute("""
                INSERT INTO backtest_runs (
                    run_id, symbol, market, strategy, params_json,
                    start_date, end_date, total_return, annual_return,
                    sharpe, max_drawdown, calmar, win_rate, profit_factor,
                    trade_count, win_count, loss_count, avg_win, avg_loss,
                    initial_capital, final_equity, run_time_sec, error_msg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, symbol, market, strategy, json.dumps(params, ensure_ascii=False),
                start_date, end_date,
                sf(metrics.get("总收益率", "0%")),
                sf(metrics.get("年化收益率", "0%")),
                sf(metrics.get("夏普比率", 0)),
                sf(metrics.get("最大回撤", "0%")),
                sf(metrics.get("卡尔玛比率", 0)),
                sf(metrics.get("胜率", "0%")),
                sf(metrics.get("盈利因子", 0)),
                si(metrics.get("交易次数", 0)),
                si(metrics.get("盈利次数", 0)),
                si(metrics.get("亏损次数", 0)),
                sf(metrics.get("平均盈利", "0")),
                sf(metrics.get("平均亏损", "0")),
                sf(metrics.get("初始资金", config.initial_capital)),
                sf(metrics.get("最终权益", config.initial_capital)),
                run_time, error,
            ))

    def _parse_pct(self, s) -> float:
        try:
            s = str(s).replace("%", "").replace("+", "")
            if s in ("∞", "inf", "-inf", "N/A", ""):
                return 0.0
            return float(s)
        except (ValueError, AttributeError):
            return 0.0

    def _parse_yuan(self, s) -> float:
        try:
            s = str(s).replace("¥", "").replace(",", "").replace("+", "")
            if s in ("∞", "inf", "-inf", "N/A", ""):
                return 0.0
            return float(s)
        except (ValueError, AttributeError):
            return 0.0

    def query(self, strategy: str = None, symbol: str = None,
              market: str = None, min_sharpe: float = None,
              min_return: float = None, limit: int = 100,
              order_by: str = "sharpe DESC") -> List[dict]:
        """查询回测结果"""
        sql = "SELECT * FROM backtest_runs WHERE error_msg IS NULL"
        params = []

        if strategy:
            sql += " AND strategy = ?"; params.append(strategy)
        if symbol:
            sql += " AND symbol = ?"; params.append(symbol)
        if market:
            sql += " AND market = ?"; params.append(market)
        if min_sharpe is not None:
            sql += " AND sharpe >= ?"; params.append(min_sharpe)
        if min_return is not None:
            sql += " AND total_return >= ?"; params.append(min_return)

        sql += f" ORDER BY {order_by} LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def ranking(self, strategy: str = None, top_n: int = 20) -> pd.DataFrame:
        """获取排名"""
        rows = self.query(strategy=strategy, limit=top_n, order_by="sharpe DESC")
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        cols = ["symbol", "market", "strategy", "total_return",
                "sharpe", "max_drawdown", "win_rate", "trade_count", "calmar"]
        return df[[c for c in cols if c in df.columns]]

    def summary(self) -> dict:
        """获取汇总统计"""
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM backtest_runs WHERE error_msg IS NULL").fetchone()[0]
            best = conn.execute(
                "SELECT symbol, strategy, sharpe, total_return FROM backtest_runs "
                "WHERE error_msg IS NULL ORDER BY sharpe DESC LIMIT 1"
            ).fetchone()
            avg_sharpe = conn.execute(
                "SELECT AVG(sharpe) FROM backtest_runs WHERE error_msg IS NULL AND trade_count > 0"
            ).fetchone()[0]

        return {
            "总回测数": count,
            "最佳策略": f"{best['strategy']} @ {best['symbol']} (夏普={best['sharpe']:.2f})" if best else "N/A",
            "平均夏普": round(avg_sharpe, 2) if avg_sharpe else 0,
        }


# ============================================================
# 策略工厂
# ============================================================

def _adaptive_params(strategy_key: str, symbol: str):
    """根据股票特征自动选择策略参数 (v4.3)"""
    try:
        from src.backtest.data_feed import get_data
        data = get_data(symbol, "A股", start_date="2022-01-01")
        if data is None or len(data) < 100:
            return {}

        close = data["close"]
        # 计算波动特征
        returns = close.pct_change().dropna()
        vol = returns.std() * (252 ** 0.5)  # 年化波动率
        # 计算趋势特征
        sma20 = close.rolling(20).mean()
        trend_strength = (close.iloc[-1] / sma20.iloc[-1] - 1)  # 距20MA偏离
        # 计算成交量特征
        avg_vol = data["volume"].mean()
        recent_vol = data["volume"].iloc[-20:].mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1

        if strategy_key == "ma_cross":
            if vol > 0.4:  # 高波动 → 慢速参数
                return {"fast_period": 8, "slow_period": 30}
            elif vol > 0.25:  # 中波动
                return {"fast_period": 5, "slow_period": 20}
            else:  # 低波动 → 快速参数
                return {"fast_period": 3, "slow_period": 12}

        elif strategy_key == "rsi":
            if vol > 0.4:
                return {"rsi_period": 7, "oversold": 25, "overbought": 75}
            else:
                return {"rsi_period": 14, "oversold": 30, "overbought": 70}

        elif strategy_key == "momentum":
            if vol > 0.4:
                return {"breakout_period": 15, "exit_period": 8}
            else:
                return {"breakout_period": 20, "exit_period": 10}

        elif strategy_key == "turtle":
            if vol > 0.4:
                return {"entry_period": 15, "exit_period": 8, "atr_stop": 2.5}
            else:
                return {"entry_period": 20, "exit_period": 10, "atr_stop": 2.0}

        elif strategy_key == "bollinger":
            if vol > 0.4:
                return {"period": 15, "std_dev": 2.5}
            else:
                return {"period": 20, "std_dev": 2.0}

    except Exception:
        pass
    return {}


def _make_strategy_instance(strategy_key: str, params: dict, symbol: str):
    """根据策略名和参数创建策略实例 — 空params时自动适配"""
    from src.config import config as cfg

    # 先试经典策略库
    if strategy_key in STRATEGIES:
        cls = STRATEGIES[strategy_key]["class"]
        # 策略集成特殊处理
        if cls is None and strategy_key == "ensemble":
            from src.strategies.ensemble import create_ensemble, EnsembleStrategy
            # 返回一个包装了集成的策略对象
            return EnsembleStrategy(symbol, params.get("threshold", 0.5))
        strategy_cfg = StrategyConfig(
            name=symbol,
            initial_capital=cfg.initial_capital,
            position_size_pct=cfg.position_size_pct,
            commission_rate=cfg.commission_rate,
        )
        # 如果用户没指定参数，使用自适应参数
        if not params:
            params = _adaptive_params(strategy_key, symbol)
        return cls(config=strategy_cfg, **params)

    # 再试预设组合策略
    if strategy_key in PRESET_STRATEGIES:
        factory = PRESET_STRATEGIES[strategy_key]["factory"]
        composer = factory()
        return composer.to_strategy(StrategyConfig(
            name=symbol,
            initial_capital=cfg.initial_capital,
            position_size_pct=cfg.position_size_pct,
        ))

    raise KeyError(f"未知策略: {strategy_key}")


# ============================================================
# 批量运行器
# ============================================================

class BatchRunner:
    """
    批量回测运行器

    用法:
        runner = BatchRunner()
        runner.add_symbols(["601398", "600519", "000858"])
        runner.add_strategies(["ma_cross", "rsi", "macd"])
        runner.run()  # 3×3=9 次回测
        runner.show_ranking()
    """

    def __init__(self):
        self.symbols: List[tuple] = []   # [(symbol, market)]
        self.strategies: List[tuple] = []  # [(strategy_key, params)]
        self.start_date = config.default_start_date
        self.end_date = None
        self.db = ResultDB()
        self.last_results: List[dict] = []

    def add_symbols(self, symbols: list, market: str = "A股"):
        """添加标的"""
        for s in symbols:
            self.symbols.append((s, market))

    def add_default_watchlist(self):
        """添加默认关注列表"""
        from src.backtest.data_feed import get_default_watchlist
        for item in get_default_watchlist():
            self.symbols.append((item["symbol"], item["market"]))

    def add_strategies(self, strategies: list, params: dict = None):
        """
        添加策略

        strategies: ["ma_cross", "rsi", "contrarian_v1", ...]
        params: {"ma_cross": {"fast_period": 10, "slow_period": 30}, ...}
        """
        params = params or {}
        for s in strategies:
            p = params.get(s, {})
            self.strategies.append((s, p))

    def add_all_strategies(self):
        """添加所有已注册的策略（经典 + 预设）"""
        for key in STRATEGIES:
            self.strategies.append((key, {}))
        for key in PRESET_STRATEGIES:
            self.strategies.append((key, {}))

    def run(self, verbose: bool = True, skip_existing: bool = True) -> pd.DataFrame:
        """
        执行批量回测

        返回: 结果 DataFrame
        """
        total = len(self.symbols) * len(self.strategies)
        if total == 0:
            print("⚠️ 没有待运行的任务，请先 add_symbols + add_strategies")
            return pd.DataFrame()

        if verbose:
            print(f"\n{'='*60}")
            print(f"  批量回测")
            print(f"  标的: {len(self.symbols)} 个 × 策略: {len(self.strategies)} 个 = {total} 次")
            print(f"  日期: {self.start_date} ~ {self.end_date or '今天'}")
            print(f"{'='*60}")

        run_id_base = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = []
        completed = 0
        errors = 0
        skipped = 0

        pbar = ProgressBar(total, desc="批量回测", verbose=verbose)

        for sym_idx, (symbol, market) in enumerate(self.symbols):
            # 加载数据（同一标的的多个策略共用）
            data, data_error = safe_call(
                get_data, symbol, market,
                start_date=self.start_date, end_date=self.end_date,
                log_error=False,
            )
            if data_error:
                if verbose:
                    pbar.update(len(self.strategies), f"数据加载失败: {symbol}")
                errors += len(self.strategies)
                continue

            for strat_idx, (strategy_key, params) in enumerate(self.strategies):
                run_id = f"{run_id_base}_{sym_idx}_{strat_idx}"

                if skip_existing:
                    existing = self.db.query(symbol=symbol, strategy=strategy_key, limit=1)
                    if existing and existing[0].get("start_date") == self.start_date:
                        skipped += 1
                        pbar.update(1, f"跳过: {symbol}@{strategy_key}")
                        continue

                with Timer(label=f"{symbol}@{strategy_key}", verbose=False) as timer:
                    try:
                        strategy = _make_strategy_instance(strategy_key, params, symbol)
                        engine = BacktestEngine(
                            initial_capital=config.initial_capital,
                            commission_rate=config.commission_rate,
                        )
                        result = engine.run(strategy, data)
                        metrics = result["metrics"]

                        self.db.save_result(
                            run_id, symbol, market, strategy_key, params,
                            self.start_date, self.end_date or "today",
                            metrics, timer.elapsed,
                        )
                        results.append({
                            "run_id": run_id, "symbol": symbol, "market": market,
                            "strategy": strategy_key, "params": params,
                            "metrics": metrics, "error": None,
                        })
                        completed += 1

                    except Exception as e:
                        logger.error(f"{symbol}@{strategy_key}: {e}")
                        self.db.save_result(
                            run_id, symbol, market, strategy_key, params,
                            self.start_date, self.end_date or "today",
                            {}, 0, str(e),
                        )
                        errors += 1

                pbar.update(1)

        pbar.close()

        self.last_results = results

        if verbose:
            print(f"\n  结果: {completed} 完成 | {skipped} 跳过 | {errors} 失败")

        df = self._to_dataframe(results)

        # === 自动生成仪表盘 ===
        if completed > 0 and not df.empty:
            try:
                from src.dashboard.visual import generate_all, build_batch_report, DASHBOARD_DIR
                import os as _os
                _os.makedirs(DASHBOARD_DIR, exist_ok=True)

                # 批量报告
                report_path = _os.path.join(DASHBOARD_DIR, "batch_report.html")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(build_batch_report(df, run_time=0))
                if verbose:
                    print(f"  📊 报告已生成: {report_path}")

                # 刷新所有仪表盘
                generate_all()
                if verbose:
                    print(f"  🖥️ 仪表盘已刷新: {DASHBOARD_DIR}/")
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ 仪表盘生成失败: {e}")

        return df

    def _to_dataframe(self, results: list) -> pd.DataFrame:
        if not results:
            return pd.DataFrame()
        rows = []
        for r in results:
            m = r["metrics"]
            row = {
                "symbol": r["symbol"],
                "market": r["market"],
                "strategy": r["strategy"],
                "总收益率": m.get("总收益率", "N/A"),
                "夏普比率": m.get("夏普比率", 0),
                "最大回撤": m.get("最大回撤", "N/A"),
                "胜率": m.get("胜率", "N/A"),
                "盈亏比": m.get("盈亏比", "N/A"),
                "交易次数": m.get("交易次数", 0),
                "卡尔玛比率": m.get("卡尔玛比率", 0),
            }
            rows.append(row)
        df = pd.DataFrame(rows)
        if not df.empty and "夏普比率" in df.columns:
            df = df.sort_values("夏普比率", ascending=False).reset_index(drop=True)
        return df

    def show_ranking(self, top_n: int = 20):
        """显示排名"""
        print(self.db.ranking(top_n=top_n).to_string())

    def show_summary(self):
        """显示汇总"""
        for k, v in self.db.summary().items():
            print(f"  {k}: {v}")


# ============================================================
# 便捷函数
# ============================================================

def quick_batch(symbols: list = None, strategies: list = None,
                start_date: str = None) -> pd.DataFrame:
    """
    一键批量回测

    示例:
        quick_batch(
            symbols=["601398", "600036", "000858"],
            strategies=["ma_cross", "rsi", "contrarian_v1"],
        )
    """
    runner = BatchRunner()

    if symbols:
        runner.add_symbols(symbols)
    else:
        runner.add_symbols(["601398", "600036", "000858", "000333", "600900"])

    if strategies:
        runner.add_strategies(strategies)
    else:
        runner.add_strategies(["ma_cross", "rsi", "momentum"])

    if start_date:
        runner.start_date = start_date

    return runner.run()


def compare_strategies(symbol: str, strategies: list = None,
                       start_date: str = None) -> pd.DataFrame:
    """
    对比同一标的上不同策略的表现

    示例:
        compare_strategies("601398", ["ma_cross", "rsi", "macd", "bollinger"])
    """
    if strategies is None:
        strategies = list(STRATEGIES.keys())

    runner = BatchRunner()
    runner.add_symbols([symbol])
    runner.add_strategies(strategies)
    if start_date:
        runner.start_date = start_date
    df = runner.run()

    if not df.empty:
        print(f"\n{'='*60}")
        print(f"  {symbol} 策略对比")
        print(f"{'='*60}")
        for _, row in df.iterrows():
            bar = "█" * int(row["夏普比率"] * 5) if row["夏普比率"] > 0 else ""
            print(f"  {row['strategy']:<20} | 夏普 {row['夏普比率']:>6.2f} | "
                  f"收益 {str(row['总收益率']):>10} | 胜率 {str(row['胜率']):>8} | {bar}")

    return df
