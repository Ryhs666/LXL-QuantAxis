"""
Live Dashboard — 实时仪表盘数据服务

提供实时 PnL、持仓、信号推送的 API 和 WebSocket 事件结构。
与现有 src/dashboard/visual.py 配合使用。

使用方式:
    from src.dashboard.live import LiveDashboard
    live = LiveDashboard()
    live.emit_pnl_update(symbol="601398", pnl=1500.5, total_equity=105000)
"""

import json
from datetime import datetime
from typing import Optional, Dict, List


class LiveDashboard:
    """实时仪表盘 — 数据聚合和事件管理"""

    def __init__(self):
        self._latest_pnl = {}
        self._latest_signals = []
        self._latest_positions = {}
        self._max_signals = 50

    # ── PnL ──────────────────────────────────────────

    def emit_pnl_update(self, symbol: str, pnl: float, pnl_pct: float = 0,
                        total_equity: float = 0, cash: float = 0):
        """记录 PnL 更新"""
        self._latest_pnl[symbol] = {
            "symbol": symbol,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 4),
            "total_equity": round(total_equity, 2),
            "cash": round(cash, 2),
            "timestamp": datetime.now().isoformat(),
        }

    # ── Signals ──────────────────────────────────────

    def emit_signal_alert(self, symbol: str, action: str, strategy: str = "",
                          price: float = 0, reason: str = ""):
        """记录信号告警"""
        alert = {
            "symbol": symbol,
            "action": action,
            "strategy": strategy,
            "price": price,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self._latest_signals.append(alert)
        if len(self._latest_signals) > self._max_signals:
            self._latest_signals = self._latest_signals[-self._max_signals:]

    # ── Positions ────────────────────────────────────

    def emit_position_update(self, symbol: str, qty: int, avg_cost: float,
                             current_price: float, pnl: float = 0):
        """记录持仓变化"""
        self._latest_positions[symbol] = {
            "symbol": symbol,
            "qty": qty,
            "avg_cost": round(avg_cost, 2),
            "current_price": round(current_price, 2),
            "pnl": round(pnl, 2),
            "timestamp": datetime.now().isoformat(),
        }

    # ── Order Status ─────────────────────────────────

    def emit_order_status(self, order_id: str, symbol: str, status: str,
                          filled_qty: int = 0, price: float = 0):
        """记录订单状态变化"""
        return {
            "order_id": order_id,
            "symbol": symbol,
            "status": status,
            "filled_qty": filled_qty,
            "price": round(price, 2),
            "timestamp": datetime.now().isoformat(),
        }

    # ── API ──────────────────────────────────────────

    def get_summary(self) -> dict:
        """当前摘要"""
        total_pnl = sum(p.get("pnl", 0) for p in self._latest_pnl.values())
        total_equity = next(
            (p.get("total_equity", 0) for p in self._latest_pnl.values()),
            0
        )
        return {
            "total_pnl": round(total_pnl, 2),
            "total_equity": round(total_equity, 2),
            "positions_count": len(self._latest_positions),
            "recent_signals": len(self._latest_signals),
            "timestamp": datetime.now().isoformat(),
        }

    def get_positions(self) -> List[dict]:
        """当前持仓列表"""
        return list(self._latest_positions.values())

    def get_recent_signals(self, limit: int = 20) -> List[dict]:
        """最近信号"""
        return self._latest_signals[-limit:]

    def get_pnl_history(self) -> List[dict]:
        """PnL 快照"""
        return list(self._latest_pnl.values())


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

live_dashboard = LiveDashboard()
