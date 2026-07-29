"""
策略存储数据库 (v5.1)
保存用户创建的策略、回测结果、复盘笔记
存于 D:/trading_data/strategy_bank.db
"""
import os, sys, sqlite3, json
from datetime import datetime
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config import config

DB_PATH = os.path.join(config.data_dir, "strategy_bank.db")


class StrategyBank:
    """策略银行 — 存储/检索/复用"""

    def __init__(self):
        self._ensure()

    def _conn(self):
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

    def _ensure(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    conditions_json TEXT NOT NULL,
                    logic TEXT DEFAULT 'weighted',
                    threshold REAL DEFAULT 3.0,
                    created_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    star INTEGER DEFAULT 0
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS strategy_backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    start_date TEXT, end_date TEXT,
                    sharpe REAL, total_return TEXT, max_dd TEXT, win_rate TEXT,
                    trade_count INTEGER, metrics_json TEXT,
                    run_at TEXT DEFAULT '',
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS trade_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT, action TEXT,
                    reason TEXT, outcome TEXT,
                    score INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '',
                    created_at TEXT DEFAULT ''
                )
            """)

    # === 策略 CRUD ===
    def save_strategy(self, name: str, conditions: list, logic: str = "weighted",
                      threshold: float = 3.0, description: str = "", tags: str = "") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conditions_json = json.dumps(conditions, ensure_ascii=False)
        with self._conn() as c:
            c.execute("""INSERT INTO strategies (name, description, conditions_json, logic, threshold, created_at, updated_at, tags)
                VALUES (?,?,?,?,?,?,?,?)""",
                (name, description, conditions_json, logic, threshold, now, now, tags))
            return c.lastrowid

    def get_strategy(self, sid: int) -> Optional[dict]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM strategies WHERE id=?", (sid,)).fetchone()
            if not r: return None
            d = dict(r)
            d["conditions"] = json.loads(d["conditions_json"])
            return d

    def list_strategies(self, tag: str = None) -> List[dict]:
        with self._conn() as c:
            if tag:
                rows = c.execute("SELECT * FROM strategies WHERE tags LIKE ? ORDER BY star DESC, updated_at DESC",
                               (f"%{tag}%",)).fetchall()
            else:
                rows = c.execute("SELECT * FROM strategies ORDER BY star DESC, updated_at DESC").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["conditions"] = json.loads(d["conditions_json"])
                result.append(d)
            return result

    def update_strategy(self, sid: int, **kwargs):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sets = []; vals = []
        for k, v in kwargs.items():
            if k == "conditions": v = json.dumps(v, ensure_ascii=False)
            sets.append(f"{k}=?"); vals.append(v)
        sets.append("updated_at=?"); vals.append(now)
        vals.append(sid)
        with self._conn() as c:
            c.execute(f"UPDATE strategies SET {','.join(sets)} WHERE id=?", vals)

    def star_strategy(self, sid: int):
        with self._conn() as c:
            c.execute("UPDATE strategies SET star=1-star WHERE id=?", (sid,))

    def delete_strategy(self, sid: int):
        with self._conn() as c:
            c.execute("DELETE FROM strategy_backtests WHERE strategy_id=?", (sid,))
            c.execute("DELETE FROM strategies WHERE id=?", (sid,))

    # === 回测记录 ===
    def save_backtest(self, strategy_id: int, symbol: str, metrics: dict,
                      start_date: str = "", end_date: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self._conn() as c:
            c.execute("""INSERT INTO strategy_backtests
                (strategy_id, symbol, start_date, end_date, sharpe, total_return, max_dd, win_rate, trade_count, metrics_json, run_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (strategy_id, symbol, start_date, end_date,
                 float(str(metrics.get("夏普比率", 0)).replace("N/A","0")),
                 str(metrics.get("总收益率", "")),
                 str(metrics.get("最大回撤", "")),
                 str(metrics.get("胜率", "")),
                 int(str(metrics.get("交易次数", 0))),
                 json.dumps(metrics, ensure_ascii=False), now))

    def get_backtests(self, strategy_id: int = None, symbol: str = None) -> List[dict]:
        with self._conn() as c:
            sql = "SELECT * FROM strategy_backtests WHERE 1=1"
            params = []
            if strategy_id: sql += " AND strategy_id=?"; params.append(strategy_id)
            if symbol: sql += " AND symbol=?"; params.append(symbol)
            sql += " ORDER BY run_at DESC LIMIT 50"
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # === 复盘笔记 ===
    def save_note(self, symbol: str, action: str, reason: str, outcome: str = "", score: int = 0):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        with self._conn() as c:
            c.execute("INSERT INTO trade_notes (date, symbol, action, reason, outcome, score, created_at) VALUES (?,?,?,?,?,?,?)",
                     (today, symbol, action, reason, outcome, score, now))

    def get_notes(self, symbol: str = None, limit: int = 30) -> List[dict]:
        with self._conn() as c:
            if symbol:
                rows = c.execute("SELECT * FROM trade_notes WHERE symbol=? ORDER BY date DESC LIMIT ?",
                               (symbol, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM trade_notes ORDER BY date DESC LIMIT ?",
                               (limit,)).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._conn() as c:
            sc = c.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
            bc = c.execute("SELECT COUNT(*) FROM strategy_backtests").fetchone()[0]
            nc = c.execute("SELECT COUNT(*) FROM trade_notes").fetchone()[0]
            return {"strategies": sc, "backtests": bc, "notes": nc}


# 全局单例
bank = StrategyBank()
