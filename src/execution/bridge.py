"""
RealtimePaperBridge — 实时信号 → 纸面交易桥接

将 StrategyEngine 产生的信号自动转化为 PaperBroker 的订单。

使用方式:
    from src.execution.bridge import RealtimePaperBridge
    bridge = RealtimePaperBridge()
    bridge.toggle_auto_trade(True)  # 开启自动纸面交易
"""

from collections import deque
from typing import Dict, Optional
from datetime import datetime


class RealtimePaperBridge:
    """实时信号 → 纸面订单桥接器"""

    def __init__(self, broker=None, strategy_engine=None):
        self.broker = broker  # PaperBroker 实例
        self.engine = strategy_engine  # StrategyEngine 实例
        self.auto_trade_enabled = False
        self.max_position_pct = 0.2
        self._signal_queue = deque(maxlen=100)

    def on_signal(self, signal: dict):
        """接收 StrategyEngine 信号并执行"""
        self._signal_queue.append(signal)

        if not self.auto_trade_enabled or not self.broker:
            return

        symbol = signal.get("symbol", "")
        action = signal.get("action", "")
        price = signal.get("price", 0)
        strategy = signal.get("strategy", "")

        if not symbol or not action or price <= 0:
            return

        if action == "BUY":
            # 计算仓位
            equity = self.broker.get_equity() or self.broker.cash
            max_cost = equity * self.max_position_pct
            quantity = int(max_cost / price / 100) * 100
            if quantity >= 100:
                self.broker.place_order(
                    symbol=symbol, action="BUY", quantity=quantity,
                    price=price, strategy_name=strategy,
                    reason=signal.get("reason", "实时信号"),
                )
        elif action == "SELL":
            try:
                positions = self.broker.get_positions()
                if positions is not None and not positions.empty:
                    match = positions[positions["symbol"] == symbol]
                    if not match.empty:
                        qty = int(match.iloc[0]["quantity"])
                        if qty > 0:
                            self.broker.place_order(
                                symbol=symbol, action="SELL", quantity=qty,
                                price=price, strategy_name=strategy,
                                reason=signal.get("reason", "实时信号"),
                            )
            except Exception:
                pass

    def toggle_auto_trade(self, enabled: bool):
        """开关自动交易"""
        self.auto_trade_enabled = enabled
        status = "ON" if enabled else "OFF"
        print(f"[Bridge] 自动纸面交易: {status}")

    def get_recent_signals(self, limit: int = 20) -> list:
        """获取最近信号"""
        return list(self._signal_queue)[-limit:]

    def stats(self) -> dict:
        """统计"""
        return {
            "auto_trade": self.auto_trade_enabled,
            "queued_signals": len(self._signal_queue),
            "broker_stats": self.broker.stats() if self.broker else {},
        }


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

bridge = RealtimePaperBridge()
