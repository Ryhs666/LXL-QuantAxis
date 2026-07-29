"""
股票名称数据库 — 输入代码自动补全名称

支持:
  - A股全市场股票列表 (从akshare下载)
  - 港股主流股票
  - 本地SQLite存储 + 模糊搜索
  - 自动更新
"""

import os, sys, sqlite3
from datetime import datetime
from typing import Optional, List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.config import config

DB_PATH = os.path.join(config.data_dir, "stock_names.db")


class StockNameDB:
    """股票名称数据库"""

    def __init__(self):
        self._ensure_db()

    def _conn(self):
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

    def _ensure_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    industry TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_name ON stocks(name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_market ON stocks(market)")

    def download_a_stocks(self, verbose=True):
        """从akshare下载A股全市场股票列表"""
        if verbose:
            print("  下载A股股票列表...")
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                raise ValueError("获取失败")

            with self._conn() as c:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                count = 0
                for _, row in df.iterrows():
                    code = str(row.get("code", "")).strip()
                    name = str(row.get("name", "")).strip()
                    if not code or not name:
                        continue
                    c.execute("""
                        INSERT OR REPLACE INTO stocks (code, name, market, updated_at)
                        VALUES (?, ?, 'A股', ?)
                    """, (code, name, now))
                    count += 1

            if verbose:
                print(f"  ✅ 已更新 {count} 只A股")

            # 也尝试获取行业分类
            self._download_industries(verbose)

            return count

        except Exception as e:
            if verbose:
                print(f"  ⚠️ A股列表下载失败: {e}")
            return 0

    def _download_industries(self, verbose=True):
        """尝试给股票标注行业"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            if df is None or df.empty:
                return

            with self._conn() as c:
                for _, row in df.iterrows():
                    name = str(row.get("板块名称", "")).strip()
                    codes_str = str(row.get("板块成分股", ""))
                    if not name or not codes_str:
                        continue
                    for code in codes_str.split(","):
                        code = code.strip()
                        if code:
                            c.execute(
                                "UPDATE stocks SET industry=? WHERE code=? AND industry=''",
                                (name, code)
                            )
            if verbose:
                print(f"  ✅ 行业分类已标注")
        except Exception:
            pass

    def download_hk_stocks(self, verbose=True):
        """下载港股列表"""
        if verbose:
            print("  下载港股列表...")
        try:
            import akshare as ak
            df = ak.stock_hk_spot_em()
            if df is None or df.empty:
                raise ValueError("获取失败")

            with self._conn() as c:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                count = 0
                for _, row in df.iterrows():
                    code = str(row.get("代码", "")).strip()
                    name = str(row.get("名称", "")).strip()
                    if not code or not name:
                        continue
                    c.execute("""
                        INSERT OR REPLACE INTO stocks (code, name, market, updated_at)
                        VALUES (?, ?, '港股', ?)
                    """, (code, name, now))
                    count += 1

            if verbose:
                print(f"  ✅ 已更新 {count} 只港股")
            return count

        except Exception as e:
            if verbose:
                print(f"  ⚠️ 港股列表下载失败: {e}")
            return 0

    def download_all(self, verbose=True):
        """下载全部股票列表"""
        if verbose:
            print("\n📥 更新股票名称数据库...")
        a = self.download_a_stocks(verbose)
        h = self.download_hk_stocks(verbose)
        if verbose:
            print(f"  总计: A股{a}只 + 港股{h}只")
        return a + h

    def lookup(self, code: str) -> Optional[Dict]:
        """精确查找股票代码"""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM stocks WHERE code=?",
                (code.strip().upper(),)
            ).fetchone()
            return dict(row) if row else None

    def search(self, keyword: str, limit: int = 20) -> List[Dict]:
        """模糊搜索 — 匹配代码或名称"""
        kw = f"%{keyword.strip().upper()}%"
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM stocks WHERE code LIKE ? OR name LIKE ? ORDER BY "
                "CASE WHEN code=? THEN 1 WHEN code LIKE ? THEN 2 ELSE 3 END LIMIT ?",
                (kw, f"%{keyword}%", keyword.strip().upper(), f"{keyword.strip().upper()}%", limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_name(self, code: str) -> str:
        """输入代码，返回名称；找不到返回代码本身"""
        r = self.lookup(code)
        return r["name"] if r else code

    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """输入前缀，返回匹配建议列表"""
        p = prefix.strip().upper()
        if not p:
            return []
        with self._conn() as c:
            rows = c.execute(
                "SELECT code, name, market FROM stocks WHERE code LIKE ? "
                "ORDER BY code LIMIT ?",
                (f"{p}%", limit)
            ).fetchall()
            if rows:
                return [f"{r['code']} - {r['name']} ({r['market']})" for r in rows]
            # 也搜名称
            rows = c.execute(
                "SELECT code, name, market FROM stocks WHERE name LIKE ? "
                "ORDER BY code LIMIT ?",
                (f"%{p}%", limit)
            ).fetchall()
            return [f"{r['code']} - {r['name']} ({r['market']})" for r in rows]

    def count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]

    def stats(self) -> dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
            markets = {}
            for row in c.execute("SELECT market, COUNT(*) as cnt FROM stocks GROUP BY market"):
                markets[row["market"]] = row["cnt"]
        return {"total": total, "by_market": markets}


# 全局单例
stock_db = StockNameDB()


def ensure_stock_db():
    """确保数据库有数据，没有则自动下载"""
    if stock_db.count() == 0:
        print("  📥 首次使用，下载股票名称库...")
        stock_db.download_all(verbose=True)
    return stock_db


def lookup_name(code: str) -> str:
    """快捷: 代码→名称"""
    return ensure_stock_db().get_name(code)
