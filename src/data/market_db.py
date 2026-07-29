"""
统一行情数据库 (v5.1)
替代CSV缓存, 所有OHLCV数据存入SQLite
支持: 建表/写入/查询/更新/批量扫描
"""
import os, sys, sqlite3
from datetime import datetime, timedelta
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config import config

DB_PATH = os.path.join(config.data_dir, "market_data.db")


class MarketDB:
    """统一行情数据库"""

    def __init__(self):
        self._ensure_db()

    def _conn(self):
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    def _ensure_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS daily_kline (
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL DEFAULT 'A股',
                    date TEXT NOT NULL,
                    open REAL, high REAL, low REAL, close REAL, volume REAL,
                    PRIMARY KEY (symbol, market, date)
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_kline_date ON daily_kline(date)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_kline_symbol ON daily_kline(symbol)")

            c.execute("""
                CREATE TABLE IF NOT EXISTS data_meta (
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL DEFAULT 'A股',
                    first_date TEXT, last_date TEXT, row_count INTEGER DEFAULT 0,
                    updated_at TEXT,
                    PRIMARY KEY (symbol, market)
                )
            """)

    # --- 写入 ---
    def insert_kline(self, symbol: str, market: str, df) -> int:
        """批量插入OHLCV数据"""
        import pandas as pd
        if df is None or len(df) == 0:
            return 0
        with self._conn() as c:
            count = 0
            for _, row in df.iterrows():
                try:
                    c.execute("""INSERT OR REPLACE INTO daily_kline
                        (symbol, market, date, open, high, low, close, volume)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (symbol, market, str(row["date"])[:10],
                         float(row.get("open",0)), float(row.get("high",0)),
                         float(row.get("low",0)), float(row.get("close",0)),
                         float(row.get("volume",0))))
                    count += 1
                except: pass
            # 更新元数据
            first = str(df["date"].iloc[0])[:10]
            last = str(df["date"].iloc[-1])[:10]
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("""INSERT OR REPLACE INTO data_meta
                (symbol, market, first_date, last_date, row_count, updated_at)
                VALUES (?,?,?,?,?,?)""",
                (symbol, market, first, last, count, now))
            return count

    # --- 查询 ---
    def get_kline(self, symbol: str, market: str = "A股",
                  start_date: str = None, end_date: str = None):
        """获取OHLCV数据, 返回DataFrame"""
        import pandas as pd
        sql = "SELECT date,open,high,low,close,volume FROM daily_kline WHERE symbol=? AND market=?"
        params = [symbol, market]
        if start_date:
            sql += " AND date >= ?"; params.append(start_date)
        if end_date:
            sql += " AND date <= ?"; params.append(end_date)
        sql += " ORDER BY date ASC"
        with self._conn() as c:
            rows = c.execute(sql, params).fetchall()
            if not rows:
                return None
            return pd.DataFrame([dict(r) for r in rows])

    def get_latest_price(self, symbol: str, market: str = "A股") -> Optional[float]:
        with self._conn() as c:
            r = c.execute("SELECT close FROM daily_kline WHERE symbol=? AND market=? ORDER BY date DESC LIMIT 1",
                         (symbol, market)).fetchone()
            return float(r["close"]) if r else None

    def get_date_range(self, symbol: str, market: str = "A股") -> tuple:
        with self._conn() as c:
            r = c.execute("SELECT first_date, last_date, row_count FROM data_meta WHERE symbol=? AND market=?",
                         (symbol, market)).fetchone()
            return (r["first_date"], r["last_date"], r["row_count"]) if r else (None, None, 0)

    # --- 批量 ---
    def get_all_symbols(self, market: str = "A股") -> List[str]:
        with self._conn() as c:
            return [r["symbol"] for r in
                    c.execute("SELECT DISTINCT symbol FROM daily_kline WHERE market=? ORDER BY symbol", (market,)).fetchall()]

    def get_meta_summary(self) -> list:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM data_meta ORDER BY symbol").fetchall()]

    def get_latest_prices_batch(self, symbols: List[str], market: str = "A股") -> dict:
        result = {}
        with self._conn() as c:
            for sym in symbols:
                r = c.execute("SELECT close FROM daily_kline WHERE symbol=? AND market=? ORDER BY date DESC LIMIT 1",
                             (sym, market)).fetchone()
                if r: result[sym] = float(r["close"])
        return result

    def needs_update(self, symbol: str, market: str = "A股") -> bool:
        """检查是否需要更新数据"""
        _, last_date, _ = self.get_date_range(symbol, market)
        if not last_date: return True
        today = datetime.now().strftime("%Y-%m-%d")
        return last_date < today

    # --- 迁移 ---
    def migrate_from_csv(self, symbol: str, market: str = "A股") -> int:
        """从CSV缓存迁移到数据库"""
        import pandas as pd
        csv_path = os.path.join(config.cache_dir, f"{market}_{symbol}_daily.csv")
        if not os.path.exists(csv_path):
            return 0
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return self.insert_kline(symbol, market, df)


# 全局单例
market_db = MarketDB()


def get_or_fetch(symbol: str, market: str = "A股",
                 start_date: str = "2020-01-01", end_date: str = None) -> "pd.DataFrame":
    """从数据库获取, 没有则从网络下载并存入数据库"""
    import pandas as pd
    from src.backtest.data_feed import get_data

    # 先查数据库
    df = market_db.get_kline(symbol, market, start_date, end_date)
    if df is not None and len(df) > 100:
        return df

    # 数据库没有, 从网络获取
    raw = get_data(symbol, market, start_date=start_date, end_date=end_date)
    if raw is not None and len(raw) > 0:
        market_db.insert_kline(symbol, market, raw)
        return market_db.get_kline(symbol, market, start_date, end_date)

    return raw
