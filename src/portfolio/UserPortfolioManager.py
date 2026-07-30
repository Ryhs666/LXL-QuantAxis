"""
用户持仓管理器

每个用户独立管理自己的持仓，底层使用 SQLAlchemy 操作 portfolios 表。
"""

from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd

from src.database import SessionLocal
from src.database.models import Portfolio


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PortfolioManager:
    """用户持仓管理器 — 增删改查 user_portfolios 表"""

    def __init__(self, user_id: int):
        self.user_id = user_id

    # ── 增 / 改 ──────────────────────────────────────────

    def add_or_update(
        self,
        symbol: str,
        quantity: int,
        price: float,
        name: str = "",
        market: str = "A股",
    ) -> dict:
        """
        添加或更新持仓。

        - 如果该 symbol 已存在，则更新数量和成本价（按加权平均）
        - 如果 quantity 为 0，则删除该持仓
        - 否则新增一条记录

        返回: {"action": "created"/"updated"/"deleted", ...}
        """
        db = SessionLocal()
        try:
            existing = (
                db.query(Portfolio)
                .filter_by(user_id=self.user_id, symbol=symbol.upper())
                .first()
            )

            if quantity <= 0:
                # 删除
                if existing:
                    db.delete(existing)
                    db.commit()
                    return {"action": "deleted", "symbol": symbol.upper()}
                return {"action": "noop", "symbol": symbol.upper()}

            if existing:
                # 更新 — 加权平均成本
                old_qty = existing.quantity
                old_cost = existing.avg_cost
                new_qty = old_qty + quantity
                new_cost = (
                    (old_cost * old_qty + price * quantity) / new_qty
                    if new_qty > 0
                    else price
                )
                existing.quantity = new_qty
                existing.avg_cost = round(new_cost, 4)
                existing.name = name or existing.name
                existing.market = market
                existing.updated_at = _utcnow()
                db.commit()
                return {
                    "action": "updated",
                    "symbol": symbol.upper(),
                    "quantity": new_qty,
                    "avg_cost": round(new_cost, 4),
                }
            else:
                # 新增
                p = Portfolio(
                    user_id=self.user_id,
                    symbol=symbol.upper(),
                    name=name or symbol,
                    market=market,
                    quantity=quantity,
                    avg_cost=price,
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                return {
                    "action": "created",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "avg_cost": price,
                    "id": p.id,
                }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── 查 ──────────────────────────────────────────────

    def get_all(self) -> pd.DataFrame:
        """
        返回当前用户所有持仓（DataFrame 格式，兼容回测引擎）。

        列: symbol, name, market, quantity, avg_cost, updated_at
        """
        db = SessionLocal()
        try:
            rows = (
                db.query(Portfolio)
                .filter_by(user_id=self.user_id)
                .filter(Portfolio.quantity > 0)
                .order_by(Portfolio.updated_at.desc())
                .all()
            )
            if not rows:
                return pd.DataFrame(
                    columns=["symbol", "name", "market", "quantity", "avg_cost"]
                )
            return pd.DataFrame([r.to_dict() for r in rows])
        finally:
            db.close()

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        根据传入的市价字典计算总资产。

        参数:
            current_prices: {"601398": 5.50, "000858": 160.00, ...}

        返回: 持仓总市值（不含现金）
        """
        df = self.get_all()
        if df.empty:
            return 0.0
        total = 0.0
        for _, row in df.iterrows():
            sym = row["symbol"]
            qty = row["quantity"]
            price = current_prices.get(sym, row["avg_cost"])
            total += qty * price
        return round(total, 2)

    # ── 删 ──────────────────────────────────────────────

    def remove(self, symbol: str) -> bool:
        """删除某只股票的持仓"""
        return self.add_or_update(symbol, quantity=0, price=0)["action"] == "deleted"

    def clear_all(self) -> int:
        """清空当前用户全部持仓，返回删除条数"""
        db = SessionLocal()
        try:
            count = (
                db.query(Portfolio)
                .filter_by(user_id=self.user_id)
                .delete()
            )
            db.commit()
            return count
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
