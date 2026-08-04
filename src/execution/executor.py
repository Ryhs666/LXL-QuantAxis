"""
OrderExecutor — 统一订单执行入口 (v2.0)

所有订单必须通过此入口提交。在订单执行前强制调用 PreTradeRiskGate 校验。

集成方式:
    from src.execution.executor import executor
    ok, order_or_reason = executor.place_order(
        symbol="600519", action="BUY", quantity=100, price=1800
    )

架构:
    OrderExecutor
      ├── PreTradeRiskGate  (风控闸门 — 6 道规则)
      ├── PaperBroker        (纸面券商 — 订单持久化)
      └── ExecutionEngine    (执行引擎 — 冰山订单/盘口/撤单)
"""

import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger("execution.executor")


class OrderExecutor:
    """
    统一订单执行器。

    所有订单提交 → gate.check_order() → 通过 → PaperBroker/ExecutionEngine
                                     → 拒绝 → 记录日志 + 返回拒绝原因
    """

    def __init__(self, gate=None, broker=None, exec_engine=None):
        """
        Args:
            gate:        PreTradeRiskGate 实例 (默认从 risk.gate 加载)
            broker:      PaperBroker 实例 (默认从 execution.paper_broker 加载)
            exec_engine: ExecutionEngine 实例 (默认从 execution.engine 加载)
        """
        self._gate = gate
        self._broker = broker
        self._exec_engine = exec_engine
        self._rejected_log = []  # 最近被拒绝的订单记录

    @property
    def gate(self):
        if self._gate is None:
            from src.risk.gate import default_gate
            self._gate = default_gate
        return self._gate

    @property
    def broker(self):
        if self._broker is None:
            from src.execution.paper_broker import PaperBroker
            self._broker = PaperBroker()
        return self._broker

    @property
    def exec_engine(self):
        if self._exec_engine is None:
            from src.execution.engine import exec_engine
            self._exec_engine = exec_engine
        return self._exec_engine

    # ── 核心: 带风控闸门的订单提交 ─────────────────────

    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float = 0.0,
        order_type: str = "market",
        strategy_name: str = "",
        reason: str = "",
        skip_risk_check: bool = False,
        data: "pd.DataFrame" = None,
        portfolio_value: float = None,
    ) -> Tuple[bool, Any]:
        """
        提交订单 (强制经过风控闸门)。

        Args:
            symbol:          股票代码
            action:          BUY / SELL / SHORT / COVER
            quantity:        数量 (股)
            price:           价格 (market 订单填 0)
            order_type:      market / limit / iceberg
            strategy_name:   策略名称
            reason:          交易理由
            skip_risk_check: 跳过风控 (仅紧急情况)
            data:            OHLCV DataFrame (iceberg 执行需要)
            portfolio_value: 组合总价值 (仓位计算需要)

        Returns:
            (成功: bool, Order对象 或 拒绝原因字符串)
        """
        # ── 1. 风控闸门校验 ──
        if not skip_risk_check:
            try:
                ok, gate_reason = self._check_risk(
                    symbol, action, quantity, price, portfolio_value
                )
                if not ok:
                    self._rejected_log.append({
                        "symbol": symbol, "action": action,
                        "quantity": quantity, "price": price,
                        "reason": gate_reason,
                        "timestamp": datetime.now().isoformat(),
                    })
                    if len(self._rejected_log) > 100:
                        self._rejected_log = self._rejected_log[-100:]
                    logger.warning(f"[Executor] 风控拦截: {symbol} {action} x{quantity} — {gate_reason}")
                    return False, gate_reason
            except Exception as e:
                logger.error(f"[Executor] 风控检查异常: {type(e).__name__}: {e}")
                # 风控异常时选择拒绝 (fail-safe)
                return False, f"风控系统异常: {type(e).__name__}"

        # ── 2. 提交到 PaperBroker ──
        try:
            order = self.broker.place_order(
                symbol=symbol, action=action, quantity=quantity,
                price=price, order_type=order_type,
                strategy_name=strategy_name, reason=reason,
                skip_risk_check=True,  # 闸门已在此层校验, 避免重复
            )
            return True, order
        except Exception as e:
            logger.error(f"[Executor] 下单异常: {type(e).__name__}: {e}")
            return False, f"下单异常: {type(e).__name__}: {e}"

    # ── 高级订单 ───────────────────────────────────────

    def place_iceberg_order(
        self,
        symbol: str,
        action: str,
        total_qty: int,
        data: "pd.DataFrame",
        portfolio_value: float = 100_000,
    ) -> Tuple[bool, Any]:
        """
        冰山订单: 自动拆分大单, 通过 ExecutionEngine 执行。

        先通过风控闸门校验整体订单, 然后委托给 ExecutionEngine.execute_buy/sell。
        """
        price = float(data["close"].iloc[-1]) if data is not None else 0.0

        # 风控校验
        ok, reason = self.place_order(
            symbol=symbol, action=action, quantity=total_qty,
            price=price, order_type="iceberg",
            skip_risk_check=False,
            data=data, portfolio_value=portfolio_value,
        )
        if not ok:
            return False, reason

        # 委托给执行引擎
        try:
            if action.upper() == "BUY":
                result = self.exec_engine.execute_buy(
                    symbol, total_qty, data, portfolio_value=portfolio_value,
                )
            elif action.upper() == "SELL":
                result = self.exec_engine.execute_sell(
                    symbol, total_qty, data, portfolio_value=portfolio_value,
                )
            else:
                return False, f"不支持的操作: {action}"

            return True, result
        except Exception as e:
            logger.error(f"[Executor] 冰山订单执行异常: {type(e).__name__}: {e}")
            return False, f"执行异常: {type(e).__name__}: {e}"

    # ── 批量下单 ───────────────────────────────────────

    def place_orders_batch(
        self, orders: list, skip_risk_check: bool = False
    ) -> Tuple[list, list]:
        """
        批量提交订单。

        Returns:
            (成功的 [(True, Order)], 失败的 [(False, reason)])
        """
        passed = []
        rejected = []
        for kw in orders:
            ok, result = self.place_order(**kw, skip_risk_check=skip_risk_check)
            if ok:
                passed.append((ok, result))
            else:
                rejected.append((ok, result))
        return passed, rejected

    # ── 内部工具 ───────────────────────────────────────

    def _check_risk(
        self, symbol: str, action: str, quantity: int,
        price: float, portfolio_value: float = None,
    ) -> Tuple[bool, str]:
        """调用风控闸门校验"""
        from src.risk.gate import check_paper_order

        side = "buy" if action.upper() in ("BUY", "SHORT") else "sell"
        order_price = price if price > 0 else 1.0

        return check_paper_order(
            {
                "symbol": symbol,
                "quantity": quantity,
                "price": order_price,
                "side": side,
                "action": action,
            },
            broker=self.broker,
            gate=self.gate,
        )

    # ── 统计与状态 ─────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "gate": self.gate.stats,
            "broker": self.broker.stats(),
            "rejected_recent": len(self._rejected_log),
            "last_rejected": self._rejected_log[-1] if self._rejected_log else None,
        }

    def get_rejected_log(self, limit: int = 20) -> list:
        return self._rejected_log[-limit:]

    def reset_daily(self):
        """每日开盘重置"""
        self.gate.reset_daily(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            current_capital=self.broker.get_equity() or self.broker.cash,
        )


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

executor = OrderExecutor()
