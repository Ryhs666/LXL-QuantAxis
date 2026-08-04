"""
Paper Broker — 统一纸面券商

整合 ExecutionEngine + TradeRepository + PortfolioManager 为一个统一的纸面交易系统。
支持订单持久化和会话恢复。

使用方式:
    from src.execution.paper_broker import PaperBroker
    broker = PaperBroker(user_id=1)
    order = broker.place_order("601398", "BUY", 1000, price=5.50)

    # 重启后恢复
    broker2 = PaperBroker.recover(user_id=1)
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict


# ═══════════════════════════════════════════
# 订单模型
# ═══════════════════════════════════════════

@dataclass
class Order:
    order_id: str = ""
    user_id: int = 1
    symbol: str = ""
    action: str = ""           # BUY / SELL / SHORT / COVER
    quantity: int = 0
    filled_qty: int = 0
    price: float = 0.0         # limit price (0 for market)
    avg_fill_price: float = 0.0
    status: str = "pending"    # pending / partial / filled / cancelled / rejected
    order_type: str = "market"  # market / limit / iceberg
    strategy_name: str = ""
    reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    filled_at: str = ""

    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())[:16]
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now


# ═══════════════════════════════════════════
# 订单持久化
# ═══════════════════════════════════════════

class OrderDB:
    """订单持久化 — SQLite"""

    DB_PATH = os.path.join(
        os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", "D:/trading_data")),
        "orders.db"
    )

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    filled_qty INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    avg_fill_price REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    order_type TEXT DEFAULT 'market',
                    strategy_name TEXT DEFAULT '',
                    reason TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    filled_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)")
            conn.commit()

    def save_order(self, order: Order):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO orders (
                    order_id, user_id, symbol, action, quantity, filled_qty,
                    price, avg_fill_price, status, order_type, strategy_name, reason,
                    created_at, updated_at, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.user_id, order.symbol, order.action,
                order.quantity, order.filled_qty, order.price, order.avg_fill_price,
                order.status, order.order_type, order.strategy_name, order.reason,
                order.created_at, order.updated_at or datetime.now().isoformat(),
                order.filled_at
            ))
            conn.commit()

    def update_order(self, order_id: str, **kwargs):
        kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [order_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE orders SET {sets} WHERE order_id = ?", vals)
            conn.commit()

    def load_pending_orders(self, user_id: int) -> List[Order]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? AND status IN ('pending', 'partial')",
                (user_id,)
            )
            return [self._row_to_order(r) for r in cur.fetchall()]

    def load_all_orders(self, user_id: int, limit: int = 100) -> List[Order]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
            return [self._row_to_order(r) for r in cur.fetchall()]

    def _row_to_order(self, row) -> Order:
        cols = ["order_id", "user_id", "symbol", "action", "quantity", "filled_qty",
                "price", "avg_fill_price", "status", "order_type", "strategy_name",
                "reason", "created_at", "updated_at", "filled_at"]
        d = dict(zip(cols, row))
        return Order(**{k: v for k, v in d.items() if k in Order.__dataclass_fields__})


# ═══════════════════════════════════════════
# 统一纸面券商
# ═══════════════════════════════════════════

class PaperBroker:
    """统一纸面券商 — 订单 + 交易记录 + 持仓管理"""

    def __init__(self, user_id: int = 1, initial_cash: float = 100_000):
        self.user_id = user_id
        self.cash = initial_cash
        self.initial_cash = initial_cash

        self.order_db = OrderDB()
        self.pending_orders: Dict[str, Order] = {}

        # 懒加载子系统
        self._trade_repo = None
        self._portfolio_mgr = None
        self._executor = None

    # ── 子系统懒加载 ─────────────────────────────────

    @property
    def trade_repo(self):
        if self._trade_repo is None:
            from src.models.trade import TradeRepository
            self._trade_repo = TradeRepository()
        return self._trade_repo

    @property
    def portfolio_mgr(self):
        if self._portfolio_mgr is None:
            from src.portfolio.UserPortfolioManager import PortfolioManager
            self._portfolio_mgr = PortfolioManager(self.user_id)
        return self._portfolio_mgr

    @property
    def executor(self):
        if self._executor is None:
            from src.execution.engine import ExecutionEngine, exec_engine
            self._executor = exec_engine  # 使用全局实例
        return self._executor

    # ── 订单操作 ──────────────────────────────────────

    def place_order(self, symbol: str, action: str, quantity: int,
                    price: float = 0.0, order_type: str = "market",
                    strategy_name: str = "", reason: str = "",
                    skip_risk_check: bool = False) -> Order:
        """下单 (自动经过风控闸门校验)"""
        # ── 风控闸门前置校验 ──
        if not skip_risk_check:
            from src.risk.gate import check_paper_order
            side = "buy" if action.upper() == "BUY" else "sell"
            ok, gate_reason = check_paper_order(
                {"symbol": symbol, "quantity": quantity, "price": price if price > 0 else 1.0,
                 "side": side, "action": action},
                broker=self,
            )
            if not ok:
                print(f"[PaperBroker] 订单被风控闸门拒绝: {gate_reason}")
                rejected = Order(
                    user_id=self.user_id, symbol=symbol, action=action,
                    quantity=quantity, price=price, order_type=order_type,
                    strategy_name=strategy_name, reason=reason,
                    status="rejected",
                )
                self.order_db.save_order(rejected)
                return rejected

        order = Order(
            user_id=self.user_id, symbol=symbol, action=action,
            quantity=quantity, price=price, order_type=order_type,
            strategy_name=strategy_name, reason=reason,
        )
        self.order_db.save_order(order)
        self.pending_orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if order_id not in self.pending_orders:
            return False
        order = self.pending_orders.pop(order_id)
        order.status = "cancelled"
        order.updated_at = datetime.now().isoformat()
        self.order_db.update_order(order_id, status="cancelled",
                                   updated_at=order.updated_at)
        return True

    def fill_order(self, order_id: str, fill_price: float,
                   fill_qty: int = None) -> Order:
        """模拟成交"""
        order = self.pending_orders.get(order_id)
        if not order:
            return None

        fill_qty = fill_qty or order.quantity
        order.filled_qty = fill_qty
        order.avg_fill_price = fill_price
        order.status = "filled"
        order.filled_at = datetime.now().isoformat()
        order.updated_at = order.filled_at

        # 更新现金
        cost = fill_price * fill_qty
        if order.action in ("BUY", "COVER"):
            self.cash -= cost
        else:
            self.cash += cost

        # 更新订单状态
        self.order_db.update_order(
            order_id, status="filled", filled_qty=fill_qty,
            avg_fill_price=fill_price, filled_at=order.filled_at,
            updated_at=order.updated_at,
        )
        self.pending_orders.pop(order_id, None)
        return order

    # ── 持仓查询 ─────────────────────────────────────

    def get_positions(self):
        """获取当前持仓"""
        try:
            return self.portfolio_mgr.get_all()
        except Exception:
            return None

    def get_equity(self, current_prices: Dict[str, float] = None) -> float:
        """计算总权益"""
        equity = self.cash
        if current_prices:
            for symbol, price in current_prices.items():
                try:
                    pos = self.portfolio_mgr.get_all()
                    if pos is not None and not pos.empty:
                        match = pos[pos["symbol"] == symbol]
                        if not match.empty:
                            equity += match.iloc[0]["quantity"] * price
                except Exception:
                    pass
        return equity

    # ── 持久化与恢复 ─────────────────────────────────

    def persist(self):
        """持久化当前所有待执行订单"""
        for order in self.pending_orders.values():
            self.order_db.save_order(order)

    @classmethod
    def recover(cls, user_id: int = 1) -> "PaperBroker":
        """从数据库恢复券商状态"""
        broker = cls(user_id=user_id)

        # 恢复待执行订单
        pending = broker.order_db.load_pending_orders(user_id)
        broker.pending_orders = {o.order_id: o for o in pending}

        # 恢复现金 (从交易记录反推)
        broker.cash = broker._compute_cash_from_trades()

        return broker

    def _compute_cash_from_trades(self) -> float:
        """从交易记录反推现金余额"""
        cash = self.initial_cash
        try:
            all_trades = self.trade_repo.find_all(limit=1000)
            for t in all_trades:
                cost = t.price * t.quantity
                if t.trade_type == "买入":
                    cash -= cost + (t.fee or 0)
                elif t.trade_type == "卖出":
                    cash += cost - (t.fee or 0)
        except Exception:
            pass
        return cash

    def stats(self) -> dict:
        """统计概览"""
        return {
            "user_id": self.user_id,
            "cash": round(self.cash, 2),
            "initial_cash": self.initial_cash,
            "pending_orders": len(self.pending_orders),
            "pnl": round(self.cash - self.initial_cash, 2),
            "pnl_pct": round((self.cash / self.initial_cash - 1) * 100, 2),
        }


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

paper_broker = PaperBroker()
