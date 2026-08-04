"""
策略存储数据库 (v5.1)
保存用户创建的策略、回测结果、复盘笔记
存于 $QUANT_DATA_DIR/strategy_bank.db
"""
import os, sys, sqlite3, json
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config import config

DB_PATH = os.path.join(config.data_dir, "strategy_bank.db")


class StrategyBank:
    """策略银行 — 存储/检索/复用"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure()

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def _ensure(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER,
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
                    owner_id INTEGER,
                    date TEXT NOT NULL,
                    symbol TEXT, action TEXT,
                    reason TEXT, outcome TEXT,
                    score INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '',
                    created_at TEXT DEFAULT ''
                )
            """)
            strategy_columns = {
                row["name"] for row in c.execute("PRAGMA table_info(strategies)")
            }
            if "owner_id" not in strategy_columns:
                c.execute("ALTER TABLE strategies ADD COLUMN owner_id INTEGER")
            note_columns = {
                row["name"] for row in c.execute("PRAGMA table_info(trade_notes)")
            }
            if "owner_id" not in note_columns:
                c.execute("ALTER TABLE trade_notes ADD COLUMN owner_id INTEGER")
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_strategies_owner_id "
                "ON strategies(owner_id)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_notes_owner_id "
                "ON trade_notes(owner_id)"
            )

    # === 策略 CRUD ===
    def save_strategy(self, name: str, conditions: list, logic: str = "weighted",
                      threshold: float = 3.0, description: str = "", tags: str = "",
                      owner_id: int = None) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conditions_json = json.dumps(conditions, ensure_ascii=False)
        with self._conn() as c:
            cursor = c.execute("""INSERT INTO strategies (owner_id, name, description, conditions_json, logic, threshold, created_at, updated_at, tags)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (owner_id, name, description, conditions_json, logic, threshold, now, now, tags))
            return cursor.lastrowid

    def get_strategy(self, sid: int, owner_id: int = None,
                     include_unowned: bool = False) -> Optional[dict]:
        with self._conn() as c:
            if owner_id is None:
                r = c.execute("SELECT * FROM strategies WHERE id=?", (sid,)).fetchone()
            elif include_unowned:
                r = c.execute(
                    "SELECT * FROM strategies WHERE id=? "
                    "AND (owner_id=? OR owner_id IS NULL)",
                    (sid, owner_id),
                ).fetchone()
            else:
                r = c.execute(
                    "SELECT * FROM strategies WHERE id=? AND owner_id=?",
                    (sid, owner_id),
                ).fetchone()
            if not r: return None
            d = dict(r)
            d["conditions"] = json.loads(d["conditions_json"])
            return d

    def list_strategies(self, tag: str = None, owner_id: int = None,
                        include_unowned: bool = False) -> List[dict]:
        with self._conn() as c:
            clauses = []
            params = []
            if owner_id is not None:
                if include_unowned:
                    clauses.append("(owner_id=? OR owner_id IS NULL)")
                else:
                    clauses.append("owner_id=?")
                params.append(owner_id)
            if tag:
                clauses.append("tags LIKE ?")
                params.append(f"%{tag}%")
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = c.execute(
                f"SELECT * FROM strategies{where} "
                "ORDER BY star DESC, updated_at DESC",
                params,
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["conditions"] = json.loads(d["conditions_json"])
                result.append(d)
            return result

    def update_strategy(self, sid: int, owner_id: int = None, **kwargs):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sets = []; vals = []
        allowed_fields = {
            "name", "description", "conditions", "logic", "threshold", "tags"
        }
        for k, v in kwargs.items():
            if k not in allowed_fields:
                raise ValueError(f"不允许更新字段: {k}")
            if k == "conditions": v = json.dumps(v, ensure_ascii=False)
            if k == "conditions": k = "conditions_json"
            sets.append(f"{k}=?"); vals.append(v)
        if not sets:
            return False
        sets.append("updated_at=?"); vals.append(now)
        vals.append(sid)
        where = "id=?"
        if owner_id is not None:
            where += " AND owner_id=?"
            vals.append(owner_id)
        with self._conn() as c:
            result = c.execute(
                f"UPDATE strategies SET {','.join(sets)} WHERE {where}", vals
            )
            return result.rowcount > 0

    def star_strategy(self, sid: int, owner_id: int = None):
        params = [sid]
        where = "id=?"
        if owner_id is not None:
            where += " AND owner_id=?"
            params.append(owner_id)
        with self._conn() as c:
            result = c.execute(
                f"UPDATE strategies SET star=1-star WHERE {where}", params
            )
            return result.rowcount > 0

    def delete_strategy(self, sid: int, owner_id: int = None,
                        include_unowned: bool = False):
        with self._conn() as c:
            if owner_id is not None:
                if include_unowned:
                    owned = c.execute(
                        "SELECT 1 FROM strategies WHERE id=? "
                        "AND (owner_id=? OR owner_id IS NULL)",
                        (sid, owner_id),
                    ).fetchone()
                else:
                    owned = c.execute(
                        "SELECT 1 FROM strategies WHERE id=? AND owner_id=?",
                        (sid, owner_id),
                    ).fetchone()
                if not owned:
                    return False
            c.execute("DELETE FROM strategy_backtests WHERE strategy_id=?", (sid,))
            result = c.execute("DELETE FROM strategies WHERE id=?", (sid,))
            return result.rowcount > 0

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
    def save_note(self, symbol: str, action: str, reason: str, outcome: str = "",
                  score: int = 0, owner_id: int = None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        with self._conn() as c:
            c.execute("INSERT INTO trade_notes (owner_id, date, symbol, action, reason, outcome, score, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (owner_id, today, symbol, action, reason, outcome, score, now))

    def get_notes(self, symbol: str = None, limit: int = 30,
                  owner_id: int = None) -> List[dict]:
        with self._conn() as c:
            clauses = []
            params = []
            if owner_id is not None:
                clauses.append("owner_id=?")
                params.append(owner_id)
            if symbol:
                clauses.append("symbol=?")
                params.append(symbol)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = c.execute(
                f"SELECT * FROM trade_notes{where} ORDER BY date DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self, owner_id: int = None, include_unowned: bool = False) -> dict:
        with self._conn() as c:
            if owner_id is None:
                sc = c.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
                bc = c.execute("SELECT COUNT(*) FROM strategy_backtests").fetchone()[0]
                nc = c.execute("SELECT COUNT(*) FROM trade_notes").fetchone()[0]
            else:
                owner_clause = "owner_id=?"
                note_owner_clause = "owner_id=?"
                if include_unowned:
                    owner_clause = "(owner_id=? OR owner_id IS NULL)"
                    note_owner_clause = "(owner_id=? OR owner_id IS NULL)"
                sc = c.execute(
                    f"SELECT COUNT(*) FROM strategies WHERE {owner_clause}",
                    (owner_id,),
                ).fetchone()[0]
                bc = c.execute("""SELECT COUNT(*) FROM strategy_backtests b
                    JOIN strategies s ON s.id=b.strategy_id
                    WHERE s.owner_id=? OR (? AND s.owner_id IS NULL)""",
                    (owner_id, include_unowned),).fetchone()[0]
                nc = c.execute(
                    f"SELECT COUNT(*) FROM trade_notes WHERE {note_owner_clause}",
                    (owner_id,),
                ).fetchone()[0]
            return {"strategies": sc, "backtests": bc, "notes": nc}

    def iter_for_memory_import(self, owner_id: int) -> List[dict]:
        """Return a read-only snapshot for the V2 Alpha Memory importer."""
        return self.list_strategies(owner_id=owner_id, include_unowned=False)


# 全局单例
bank = StrategyBank()
