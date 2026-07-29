"""
交易数据模型 + SQLite 数据访问层

核心功能：
- Trade 数据类：一笔交易的所有字段
- TradeRepository：数据库的增删改查、买卖配对、盈亏计算
"""

import sqlite3
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Trade:
    """一笔交易记录"""
    market: str                  # "A股" / "美股"
    symbol: str                  # 股票代码
    name: str                    # 股票名称
    direction: str               # "做多" / "做空"
    trade_type: str              # "买入" / "卖出"
    trade_date: str              # 交易日期 YYYY-MM-DD
    price: float                 # 成交价格
    quantity: int                # 成交股数
    fee: float = 0.0             # 手续费
    reason: str = ""             # 交易理由
    strategy_name: str = ""      # 所属策略
    tags: str = ""               # 标签，逗号分隔
    review_notes: str = ""       # 复盘笔记
    review_score: int = 0        # 自我评分 1-5，0 表示未评分
    paired_trade_id: Optional[int] = None  # 配对的买卖单 ID
    id: Optional[int] = None     # 数据库主键（新建时为空）
    created_at: str = ""         # 创建时间
    updated_at: str = ""         # 最后修改时间

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.updated_at:
            self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def is_buy(self) -> bool:
        return self.trade_type == "买入"

    @property
    def is_sell(self) -> bool:
        return self.trade_type == "卖出"


# ============================================================
# 数据访问层
# ============================================================

class TradeRepository:
    """交易记录的 SQLite 存储，提供完整的增删改查"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = r"D:\trading_data"
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "trades.db")
        self.db_path = db_path
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ---- 建表 ----

    def _ensure_table(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    market          TEXT    NOT NULL,
                    symbol          TEXT    NOT NULL,
                    name            TEXT    NOT NULL,
                    direction       TEXT    NOT NULL DEFAULT '做多',
                    trade_type      TEXT    NOT NULL,
                    trade_date      TEXT    NOT NULL,
                    price           REAL    NOT NULL,
                    quantity        INTEGER NOT NULL,
                    fee             REAL    DEFAULT 0,
                    reason          TEXT    DEFAULT '',
                    strategy_name   TEXT    DEFAULT '',
                    tags            TEXT    DEFAULT '',
                    review_notes    TEXT    DEFAULT '',
                    review_score    INTEGER DEFAULT 0,
                    paired_trade_id INTEGER DEFAULT NULL,
                    created_at      TEXT    DEFAULT '',
                    updated_at      TEXT    DEFAULT ''
                )
            """)

    # ---- 增 ----

    def add(self, trade: Trade) -> int:
        """新增一条交易记录，返回自增 ID"""
        with self._get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO trades
                    (market, symbol, name, direction, trade_type, trade_date,
                     price, quantity, fee, reason, strategy_name, tags,
                     review_notes, review_score, paired_trade_id,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.market, trade.symbol, trade.name, trade.direction,
                trade.trade_type, trade.trade_date, trade.price, trade.quantity,
                trade.fee, trade.reason, trade.strategy_name, trade.tags,
                trade.review_notes, trade.review_score, trade.paired_trade_id,
                trade.created_at, trade.updated_at,
            ))
            return cur.lastrowid

    # ---- 删 ----

    def delete(self, trade_id: int):
        """删除一条交易记录，同时解除其他记录对它的配对引用"""
        with self._get_conn() as conn:
            conn.execute("UPDATE trades SET paired_trade_id = NULL WHERE paired_trade_id = ?", (trade_id,))
            conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))

    # ---- 改 ----

    def update(self, trade: Trade):
        """更新一条交易记录（按 trade.id）"""
        if trade.id is None:
            raise ValueError("更新需要 trade.id")
        trade.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE trades SET
                    market=?, symbol=?, name=?, direction=?, trade_type=?,
                    trade_date=?, price=?, quantity=?, fee=?, reason=?,
                    strategy_name=?, tags=?, review_notes=?, review_score=?,
                    paired_trade_id=?, updated_at=?
                WHERE id=?
            """, (
                trade.market, trade.symbol, trade.name, trade.direction,
                trade.trade_type, trade.trade_date, trade.price, trade.quantity,
                trade.fee, trade.reason, trade.strategy_name, trade.tags,
                trade.review_notes, trade.review_score, trade.paired_trade_id,
                trade.updated_at, trade.id,
            ))

    def update_review(self, trade_id: int, review_notes: str, review_score: int):
        """更新复盘笔记和评分"""
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE trades SET review_notes=?, review_score=?, updated_at=?
                WHERE id=?
            """, (review_notes, review_score, updated_at, trade_id))

    def set_paired_trade(self, buy_id: int, sell_id: int):
        """将一笔买入和一笔卖出配对"""
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE trades SET paired_trade_id=?, updated_at=? WHERE id=?",
                (sell_id, updated_at, buy_id))
            conn.execute(
                "UPDATE trades SET paired_trade_id=?, updated_at=? WHERE id=?",
                (buy_id, updated_at, sell_id))

    # ---- 查 ----

    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """按 ID 查询单条记录"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
            return self._row_to_trade(row) if row else None

    def find_all(self,
                 market: str = None,
                 symbol: str = None,
                 trade_type: str = None,
                 strategy_name: str = None,
                 date_from: str = None,
                 date_to: str = None,
                 limit: int = 100) -> List[Trade]:
        """多条件查询交易记录"""
        sql = "SELECT * FROM trades WHERE 1=1"
        params = []

        if market:
            sql += " AND market = ?"; params.append(market)
        if symbol:
            sql += " AND symbol = ?"; params.append(symbol)
        if trade_type:
            sql += " AND trade_type = ?"; params.append(trade_type)
        if strategy_name:
            sql += " AND strategy_name = ?"; params.append(strategy_name)
        if date_from:
            sql += " AND trade_date >= ?"; params.append(date_from)
        if date_to:
            sql += " AND trade_date <= ?"; params.append(date_to)

        sql += " ORDER BY trade_date DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_trade(r) for r in rows]

    def find_open_positions(self, market: str = None) -> List[Trade]:
        """查找未配对的买入记录（即当前持仓）"""
        sql = """
            SELECT * FROM trades
            WHERE trade_type = '买入'
              AND paired_trade_id IS NULL
        """
        params = []
        if market:
            sql += " AND market = ?"
            params.append(market)
        sql += " ORDER BY trade_date DESC"

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_trade(r) for r in rows]

    def find_paired_trades(self, buy_id: int) -> Optional[Trade]:
        """查找某笔买入对应的卖出记录"""
        buy = self.get_by_id(buy_id)
        if buy and buy.paired_trade_id:
            return self.get_by_id(buy.paired_trade_id)
        return None

    def calc_pnl(self, buy_id: int) -> Optional[dict]:
        """计算一笔买入的盈亏（需已配对卖出）"""
        buy = self.get_by_id(buy_id)
        if not buy or not buy.paired_trade_id:
            return None
        sell = self.get_by_id(buy.paired_trade_id)
        if not sell:
            return None

        gross_pnl = (sell.price - buy.price) * buy.quantity
        net_pnl = gross_pnl - buy.fee - sell.fee
        pnl_pct = (sell.price / buy.price - 1) * 100

        return {
            "buy_id": buy.id,
            "sell_id": sell.id,
            "symbol": buy.symbol,
            "name": buy.name,
            "market": buy.market,
            "buy_date": buy.trade_date,
            "sell_date": sell.trade_date,
            "buy_price": buy.price,
            "sell_price": sell.price,
            "quantity": buy.quantity,
            "gross_pnl": round(gross_pnl, 2),
            "fee": round(buy.fee + sell.fee, 2),
            "net_pnl": round(net_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "direction": buy.direction,
        }

    def get_all_pnl(self, market: str = None) -> List[dict]:
        """获取所有已完成交易（已配对）的盈亏汇总"""
        sql = "SELECT * FROM trades WHERE trade_type = '买入' AND paired_trade_id IS NOT NULL"
        params = []
        if market:
            sql += " AND market = ?"
            params.append(market)
        sql += " ORDER BY trade_date DESC"

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            pnl = self.calc_pnl(row["id"])
            if pnl:
                results.append(pnl)
        return results

    def count(self, **filters) -> int:
        """统计符合条件的记录数"""
        sql = "SELECT COUNT(*) FROM trades WHERE 1=1"
        params = []
        for key, val in filters.items():
            sql += f" AND {key} = ?"
            params.append(val)

        with self._get_conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    # ---- 工具 ----

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """将数据库行转为 Trade 对象"""
        return Trade(
            id=row["id"],
            market=row["market"],
            symbol=row["symbol"],
            name=row["name"],
            direction=row["direction"],
            trade_type=row["trade_type"],
            trade_date=row["trade_date"],
            price=row["price"],
            quantity=row["quantity"],
            fee=row["fee"],
            reason=row["reason"],
            strategy_name=row["strategy_name"],
            tags=row["tags"],
            review_notes=row["review_notes"],
            review_score=row["review_score"],
            paired_trade_id=row["paired_trade_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def export_csv(self, filepath: str):
        """导出全部记录为 CSV"""
        import csv
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM trades ORDER BY trade_date DESC, id DESC").fetchall()
        if not rows:
            return
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            writer.writerows([tuple(r) for r in rows])

    def import_csv(self, filepath: str) -> int:
        """从 CSV 批量导入，返回导入条数"""
        import csv
        count = 0
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trade = Trade(
                    market=row.get("market", ""),
                    symbol=row.get("symbol", ""),
                    name=row.get("name", ""),
                    direction=row.get("direction", "做多"),
                    trade_type=row.get("trade_type", ""),
                    trade_date=row.get("trade_date", ""),
                    price=float(row.get("price", 0)),
                    quantity=int(row.get("quantity", 0)),
                    fee=float(row.get("fee", 0)),
                    reason=row.get("reason", ""),
                    strategy_name=row.get("strategy_name", ""),
                    tags=row.get("tags", ""),
                    review_notes=row.get("review_notes", ""),
                    review_score=int(row.get("review_score", 0)),
                )
                self.add(trade)
                count += 1
        return count
