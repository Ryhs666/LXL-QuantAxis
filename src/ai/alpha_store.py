"""
Alpha Memory — 信号记忆数据库

记录每条 alpha 信号的完整生命周期:
  生成 → 预期收益 → 实际结果 → 反馈

作为整个 Alpha Memory 闭环的中心存储:
  - AlphaSignalStore: 信号记录与查询
  - 按因子/市场状态/来源聚合胜率
  - IC 衰减时间线
  - 因子健康度评估

使用方式:
    from src.ai.alpha_store import alpha_store
    alpha_store.record_signal(source="factor_calc", symbol="601398", ...)
    stats = alpha_store.get_win_rate_by_factor()
"""

import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict


# ============================================================
# 数据模型
# ============================================================

@dataclass
class AlphaSignal:
    """单条 alpha 信号记录"""
    source: str              # "factor_calc" | "ai_miner" | "sentiment" | "strategy_engine" | "composer"
    symbol: str
    market: str = "A股"
    date: str = ""           # YYYY-MM-DD
    factor_name: str = ""    # 主导因子
    factor_values: str = ""  # JSON: {factor_name: value}
    market_regime: int = -1  # 0-3 (来自 MarketRegimeDetector), -1=未检测
    regime_detail: str = ""  # JSON 状态详情
    expected_return: float = 0.0
    actual_return: float = 0.0
    signal_action: str = ""  # BUY / SELL / HOLD
    signal_strength: float = 0.0  # 0.0-1.0
    outcome: str = ""        # "" / "win" / "loss" / "expired"
    outcome_pnl_pct: float = 0.0
    strategy_name: str = ""
    feedback_applied: int = 0  # 已用于反馈回路?
    signal_id: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = str(uuid.uuid4())[:12]
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AlphaSignalStore:
    """Alpha 信号记忆 — SQLite 持久化"""

    DB_PATH = os.path.join(
        os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", "D:/trading_data")),
        "alpha_memory.db"
    )

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── 初始化 ──────────────────────────────────────────

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS alpha_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT DEFAULT 'A股',
                    date TEXT NOT NULL,
                    factor_name TEXT DEFAULT '',
                    factor_values TEXT DEFAULT '{}',
                    market_regime INTEGER DEFAULT -1,
                    regime_detail TEXT DEFAULT '{}',
                    expected_return REAL DEFAULT 0.0,
                    actual_return REAL DEFAULT 0.0,
                    signal_action TEXT DEFAULT '',
                    signal_strength REAL DEFAULT 0.0,
                    outcome TEXT DEFAULT '',
                    outcome_pnl_pct REAL DEFAULT 0.0,
                    strategy_name TEXT DEFAULT '',
                    feedback_applied INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            # 索引
            for idx in [
                "idx_as_symbol_date ON alpha_signals(symbol, date)",
                "idx_as_source_date ON alpha_signals(source, date)",
                "idx_as_regime_date ON alpha_signals(market_regime, date)",
                "idx_as_outcome ON alpha_signals(outcome)",
                "idx_as_factor ON alpha_signals(factor_name)",
                "idx_as_date ON alpha_signals(date)",
            ]:
                try:
                    c.execute(f"CREATE INDEX IF NOT EXISTS {idx}")
                except sqlite3.OperationalError:
                    pass
            c.commit()

    # ── 写入 ────────────────────────────────────────────

    def record_signal(self, **kwargs) -> str:
        """记录一条 alpha 信号，返回 signal_id"""
        sig = AlphaSignal(**{k: v for k, v in kwargs.items()
                             if k in AlphaSignal.__dataclass_fields__})
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO alpha_signals (
                    signal_id, source, symbol, market, date,
                    factor_name, factor_values, market_regime, regime_detail,
                    expected_return, actual_return, signal_action, signal_strength,
                    outcome, outcome_pnl_pct, strategy_name, feedback_applied,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sig.signal_id, sig.source, sig.symbol, sig.market, sig.date,
                sig.factor_name, sig.factor_values, sig.market_regime, sig.regime_detail,
                sig.expected_return, sig.actual_return, sig.signal_action, sig.signal_strength,
                sig.outcome, sig.outcome_pnl_pct, sig.strategy_name, sig.feedback_applied,
                sig.created_at, sig.created_at,
            ))
            c.commit()
        return sig.signal_id

    def record_batch(self, signals: List[dict]) -> List[str]:
        """批量记录信号"""
        ids = []
        with self._conn() as c:
            for kw in signals:
                sig = AlphaSignal(**{k: v for k, v in kw.items()
                                     if k in AlphaSignal.__dataclass_fields__})
                c.execute("""
                    INSERT OR REPLACE INTO alpha_signals (
                        signal_id, source, symbol, market, date,
                        factor_name, factor_values, market_regime, regime_detail,
                        expected_return, actual_return, signal_action, signal_strength,
                        outcome, outcome_pnl_pct, strategy_name, feedback_applied,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sig.signal_id, sig.source, sig.symbol, sig.market, sig.date,
                    sig.factor_name, sig.factor_values, sig.market_regime, sig.regime_detail,
                    sig.expected_return, sig.actual_return, sig.signal_action, sig.signal_strength,
                    sig.outcome, sig.outcome_pnl_pct, sig.strategy_name, sig.feedback_applied,
                    sig.created_at, sig.created_at,
                ))
                ids.append(sig.signal_id)
            c.commit()
        return ids

    def update_outcome(self, signal_id: str, actual_return: float, outcome: str,
                       outcome_pnl_pct: float = 0.0):
        """更新信号的实际结果"""
        with self._conn() as c:
            c.execute("""
                UPDATE alpha_signals
                SET actual_return = ?, outcome = ?, outcome_pnl_pct = ?,
                    updated_at = ?
                WHERE signal_id = ?
            """, (actual_return, outcome, outcome_pnl_pct,
                  datetime.now().isoformat(), signal_id))
            c.commit()

    def mark_feedback_applied(self, signal_id: str):
        """标记该信号已用于反馈回路"""
        with self._conn() as c:
            c.execute("""
                UPDATE alpha_signals
                SET feedback_applied = 1, updated_at = ?
                WHERE signal_id = ?
            """, (datetime.now().isoformat(), signal_id))
            c.commit()

    # ── 查询 ────────────────────────────────────────────

    def query_by_regime(self, regime_id: int, days: int = 90) -> List[dict]:
        """按市场状态查询信号"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT * FROM alpha_signals
                WHERE market_regime = ? AND date >= ?
                ORDER BY date DESC
                LIMIT 500
            """, (regime_id, cutoff))
            return self._rows_to_dicts(cur.fetchall())

    def query_by_source(self, source: str, days: int = 90) -> List[dict]:
        """按来源查询信号"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT * FROM alpha_signals
                WHERE source = ? AND date >= ?
                ORDER BY date DESC
                LIMIT 500
            """, (source, cutoff))
            return self._rows_to_dicts(cur.fetchall())

    def query_by_factor(self, factor_name: str, days: int = 90) -> List[dict]:
        """按因子名查询"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT * FROM alpha_signals
                WHERE factor_name LIKE ? AND date >= ?
                ORDER BY date DESC
                LIMIT 500
            """, (f"%{factor_name}%", cutoff))
            return self._rows_to_dicts(cur.fetchall())

    def query_by_symbol(self, symbol: str, days: int = 90) -> List[dict]:
        """按股票代码查询"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT * FROM alpha_signals
                WHERE symbol = ? AND date >= ?
                ORDER BY date DESC
                LIMIT 500
            """, (symbol, cutoff))
            return self._rows_to_dicts(cur.fetchall())

    def get_recent(self, limit: int = 50) -> List[dict]:
        """最近 N 条信号"""
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT * FROM alpha_signals
                ORDER BY date DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            return self._rows_to_dicts(cur.fetchall())

    # ── 聚合分析 ────────────────────────────────────────

    def get_win_rate_by_factor(self, days: int = 90) -> Dict[str, dict]:
        """按因子聚合胜率"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT
                    factor_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                    AVG(CASE WHEN outcome != '' THEN outcome_pnl_pct END) as avg_pnl,
                    AVG(signal_strength) as avg_strength
                FROM alpha_signals
                WHERE date >= ? AND factor_name != '' AND outcome != ''
                GROUP BY factor_name
                ORDER BY total DESC
            """, (cutoff,))
            rows = cur.fetchall()
        return {
            r[0]: {
                "total": r[1], "wins": r[2], "losses": r[3],
                "win_rate": round(r[2] / max(r[1], 1), 3),
                "avg_pnl_pct": round(r[4] or 0, 4),
                "avg_strength": round(r[5] or 0, 3),
            }
            for r in rows
        }

    def get_regime_performance_matrix(self, days: int = 180) -> Dict[int, dict]:
        """市场状态表现矩阵: regime_id → {win_rate, avg_return, best_factors}"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT
                    market_regime,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    AVG(CASE WHEN outcome != '' THEN outcome_pnl_pct END) as avg_pnl,
                    AVG(signal_strength) as avg_strength
                FROM alpha_signals
                WHERE date >= ? AND outcome != '' AND market_regime >= 0
                GROUP BY market_regime
            """, (cutoff,))
            rows = cur.fetchall()
        result = {}
        for r in rows:
            rid = r[0]
            # 获取该状态下最佳因子
            best = self._best_factors_for_regime(rid, days)
            result[rid] = {
                "total_signals": r[1],
                "wins": r[2],
                "win_rate": round(r[2] / max(r[1], 1), 3),
                "avg_pnl_pct": round(r[3] or 0, 4),
                "avg_signal_strength": round(r[4] or 0, 3),
                "best_factors": best,
            }
        return result

    def _best_factors_for_regime(self, regime_id: int, days: int = 180) -> List[str]:
        """某市场状态下胜率最高的因子"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT factor_name,
                       CAST(SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as wr
                FROM alpha_signals
                WHERE market_regime = ? AND date >= ? AND outcome != '' AND factor_name != ''
                GROUP BY factor_name
                HAVING COUNT(*) >= 3
                ORDER BY wr DESC
                LIMIT 5
            """, (regime_id, cutoff))
            return [r[0] for r in cur.fetchall()]

    def get_ic_decay_timeline(self, factor_name: str, days: int = 90) -> List[dict]:
        """因子的 IC 衰减时间线"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT date, factor_values, outcome, outcome_pnl_pct
                FROM alpha_signals
                WHERE factor_name LIKE ? AND date >= ?
                ORDER BY date ASC
            """, (f"%{factor_name}%", cutoff))
            rows = cur.fetchall()
        return [
            {"date": r[0], "factor_values": r[1], "outcome": r[2], "pnl_pct": r[3]}
            for r in rows
        ]

    def get_factor_health(self) -> Dict[str, dict]:
        """所有因子的健康度评估"""
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT
                    factor_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) as losses,
                    AVG(CASE WHEN outcome != '' THEN outcome_pnl_pct END) as avg_pnl,
                    MAX(date) as last_seen
                FROM alpha_signals
                WHERE factor_name != ''
                GROUP BY factor_name
            """)
            rows = cur.fetchall()
        result = {}
        for r in rows:
            total = r[1]
            wins = r[2] if r[2] else 0
            wr = wins / max(total, 1)
            # 评估健康度
            if wr >= 0.55:
                health = "strong"
            elif wr >= 0.45:
                health = "moderate"
            elif wr >= 0.35:
                health = "weak"
            else:
                health = "ineffective"

            # 检查是否已多日未出现
            last_seen = r[5]
            stale = False
            if last_seen:
                try:
                    last_date = datetime.strptime(last_seen, "%Y-%m-%d")
                    stale = (datetime.now() - last_date).days > 14
                except ValueError:
                    pass

            result[r[0]] = {
                "total": total, "wins": wins, "losses": r[3] or 0,
                "win_rate": round(wr, 3),
                "avg_pnl_pct": round(r[4] or 0, 4),
                "last_seen": last_seen or "",
                "health": "stale" if stale else health,
            }
        return result

    def get_source_stats(self, days: int = 90) -> Dict[str, dict]:
        """按来源聚合统计"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT
                    source,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    AVG(signal_strength) as avg_strength
                FROM alpha_signals
                WHERE date >= ?
                GROUP BY source
            """, (cutoff,))
            rows = cur.fetchall()
        return {
            r[0]: {
                "total": r[1], "wins": r[2] or 0,
                "win_rate": round((r[2] or 0) / max(r[1], 1), 3),
                "avg_strength": round(r[3] or 0, 3),
            }
            for r in rows
        }

    # ── 维护 ────────────────────────────────────────────

    def count(self, **filters) -> int:
        """统计信号数量，支持按 source/symbol/outcome 过滤"""
        query = "SELECT COUNT(*) FROM alpha_signals WHERE 1=1"
        params = []
        for k, v in filters.items():
            query += f" AND {k} = ?"
            params.append(v)
        with self._conn() as conn:
            cur = conn.execute(query, params)
            return cur.fetchone()[0]

    def purge_older_than(self, days: int) -> int:
        """清理过期信号，返回删除数量"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM alpha_signals WHERE date < ?", (cutoff,))
            deleted = cur.rowcount
            conn.commit()
        return deleted

    def stats(self) -> dict:
        """总体统计概览"""
        with self._conn() as conn:
            cur1 = conn.execute("SELECT COUNT(*) FROM alpha_signals")
            total = cur1.fetchone()[0]
            cur2 = conn.execute("SELECT COUNT(DISTINCT symbol) FROM alpha_signals")
            symbols = cur2.fetchone()[0]
            cur3 = conn.execute("SELECT COUNT(DISTINCT factor_name) FROM alpha_signals WHERE factor_name != ''")
            factors = cur3.fetchone()[0]
            cur4 = conn.execute("""
                SELECT outcome, COUNT(*) FROM alpha_signals
                WHERE outcome != '' GROUP BY outcome
            """)
            outcomes = dict(cur4.fetchall())
        return {
            "total_signals": total,
            "unique_symbols": symbols,
            "unique_factors": factors,
            "outcomes": outcomes,
            "db_path": self.db_path,
        }

    # ── 内部工具 ────────────────────────────────────────

    def _rows_to_dicts(self, rows) -> List[dict]:
        if not rows:
            return []
        cols = [
            "id", "signal_id", "source", "symbol", "market", "date",
            "factor_name", "factor_values", "market_regime", "regime_detail",
            "expected_return", "actual_return", "signal_action", "signal_strength",
            "outcome", "outcome_pnl_pct", "strategy_name", "feedback_applied",
            "created_at", "updated_at",
        ]
        return [dict(zip(cols, r)) for r in rows]


# ============================================================
# 全局单例
# ============================================================

alpha_store = AlphaSignalStore()