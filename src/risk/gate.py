# -*- coding: utf-8 -*-
"""
PreTradeRiskGate — 交易前风险强制闸门

在每笔订单执行前拦截违反风控规则的订单，返回 (是否通过, 拒绝原因)。

集成点:
  - PaperBroker.place_order() — 纸面交易前校验
  - BacktestEngine 信号执行 — 回测中的风控拦截
  - RealtimePaperBridge.on_signal() — 实时自动交易前校验

使用方式:
    from src.risk.gate import PreTradeRiskGate, default_gate
    ok, reason = default_gate.check_order(order, positions, total_value, cash)
"""

from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger("risk.gate")


class PreTradeRiskGate:
    """
    风控闸门 — 每笔订单执行前强制校验。

    规则:
      1. 订单合法性 (价格>0, 数量>0)
      2. 总仓位上限 (买入后不超过 max_total_position_pct)
      3. 单票集中度 (单票持仓市值不超过 max_single_stock_pct)
      4. 账户回撤硬止损 (回撤超过 max_drawdown_pct 拒绝所有买入)
      5. 现金充足性 (买入金额不超过可用现金)
      6. 日内最大亏损 (当日累计亏损超过阈值, 冻结交易)
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 风控配置, 支持以下键:
                max_total_position_pct:  总仓位上限 (0~1), 默认 0.95
                max_single_stock_pct:    单票持仓市值占比上限 (0~1), 默认 0.10
                max_daily_loss_pct:      日内最大亏损比例, 默认 0.05
                max_drawdown_pct:        账户最大回撤硬止损线, 默认 0.20
                initial_capital:         初始资金, 默认 1,000,000
                min_order_value:         最小订单金额, 默认 0 (不过滤)
                max_order_value_pct:     单笔订单最大占比, 默认 0.30
                blocked_symbols:         禁止交易的标的列表, 默认 []
        """
        config = config or {}
        self.max_total_position_pct = config.get("max_total_position_pct", 0.95)
        self.max_single_stock_pct = config.get("max_single_stock_pct", 0.10)
        self.max_daily_loss_pct = config.get("max_daily_loss_pct", 0.05)
        self.max_drawdown_pct = config.get("max_drawdown_pct", 0.20)
        self.initial_capital = config.get("initial_capital", 1_000_000.0)
        self.min_order_value = config.get("min_order_value", 0.0)
        self.max_order_value_pct = config.get("max_order_value_pct", 0.30)
        self.blocked_symbols = set(config.get("blocked_symbols", []))

        # 运行时状态
        self._peak_capital = self.initial_capital
        self._daily_start_capital = self.initial_capital
        self._today_pnl = 0.0
        self._today_date = None
        self._total_checks = 0
        self._total_rejected = 0

    # ── 生命周期 ─────────────────────────────────────────

    def reset_daily(self, current_date: str = None, current_capital: float = None):
        """每日开盘前调用，重置日内统计"""
        self._today_date = current_date or datetime.now().strftime("%Y-%m-%d")
        if current_capital is not None:
            self._daily_start_capital = current_capital
        self._today_pnl = 0.0
        logger.info(f"[RiskGate] 日内风控重置, 基准资金: {self._daily_start_capital:,.0f}")

    def update_pnl(self, pnl: float):
        """更新当日已实现盈亏 (在订单成交后调用)"""
        self._today_pnl += pnl

    def update_equity(self, current_equity: float):
        """更新权益峰值追踪"""
        if current_equity > self._peak_capital:
            self._peak_capital = current_equity

    # ── 核心校验 ─────────────────────────────────────────

    def check_order(
        self,
        order: Dict[str, Any],
        current_positions: Dict[str, float],
        current_total_value: float,
        current_cash: float,
    ) -> Tuple[bool, str]:
        """
        校验单笔订单。

        Args:
            order: 订单字典 {symbol, quantity, price, side ('buy'/'sell'/...)}
            current_positions: {symbol: market_value} 当前持仓市值
            current_total_value: 账户当前总资产 (现金 + 持仓市值)
            current_cash: 账户当前现金

        Returns:
            (通过: bool, 原因: str)
        """
        self._total_checks += 1

        symbol = str(order.get("symbol", ""))
        price = float(order.get("price", 0))
        quantity = abs(int(order.get("quantity", 0)))
        side = str(order.get("side", order.get("action", "buy"))).lower()
        is_buy = side in ("buy", "买入")
        is_sell = side in ("sell", "卖出", "cover", "short")

        # ---- 0. 基础合法性 ----
        if not symbol:
            return False, "订单缺少 symbol"
        if price <= 0 or quantity <= 0:
            return False, f"订单参数异常: price={price}, qty={quantity}"

        order_value = price * quantity

        # 黑名单
        if symbol in self.blocked_symbols:
            return False, f"标的 {symbol} 在禁止交易黑名单中"

        # 最小金额
        if self.min_order_value > 0 and order_value < self.min_order_value:
            return False, f"订单金额 {order_value:,.0f} 低于最小限制 {self.min_order_value:,.0f}"

        # ---- 1. 总仓位上限 (仅买入) ----
        if is_buy:
            current_position_value = sum(current_positions.values())
            new_position_value = current_position_value + order_value
            position_pct = new_position_value / current_total_value if current_total_value > 0 else 1.0
            if position_pct > self.max_total_position_pct:
                return False, (
                    f"总仓位超限: {position_pct:.1%} > {self.max_total_position_pct:.1%} "
                    f"(新建{order_value:,.0f} + 现有{current_position_value:,.0f})"
                )

        # ---- 2. 单票集中度 (仅买入) ----
        if is_buy:
            current_stock_value = current_positions.get(symbol, 0.0)
            new_stock_value = current_stock_value + order_value
            stock_pct = new_stock_value / current_total_value if current_total_value > 0 else 1.0
            if stock_pct > self.max_single_stock_pct:
                return False, (
                    f"单票 {symbol} 仓位超限: {stock_pct:.1%} > {self.max_single_stock_pct:.1%} "
                    f"(现有{current_stock_value:,.0f} + 新建{order_value:,.0f})"
                )

        # 单笔订单上限
        if is_buy:
            order_pct = order_value / current_total_value if current_total_value > 0 else 1.0
            if order_pct > self.max_order_value_pct:
                return False, f"单笔订单占比 {order_pct:.1%} > {self.max_order_value_pct:.1%}"

        # ---- 3. 账户回撤硬止损 ----
        if self._peak_capital > 0:
            current_drawdown = 1.0 - (current_total_value / self._peak_capital)
            if current_drawdown > self.max_drawdown_pct:
                # 卖出/平仓不受回撤限制 (需要止损时允许卖)
                if is_buy:
                    return False, (
                        f"账户回撤超限: {current_drawdown:.2%} > {self.max_drawdown_pct:.2%} "
                        f"(峰值{self._peak_capital:,.0f} → 当前{current_total_value:,.0f})"
                    )

        # ---- 4. 日内最大亏损 ----
        if self._today_date:
            daily_loss = -self._today_pnl  # 正值表示亏损
            daily_loss_pct = daily_loss / self._daily_start_capital if self._daily_start_capital > 0 else 0
            if daily_loss_pct > self.max_daily_loss_pct:
                return False, (
                    f"日内亏损超限: {daily_loss_pct:.2%} > {self.max_daily_loss_pct:.2%} "
                    f"(亏损{daily_loss:,.0f}, 剩余额度{self._daily_start_capital*self.max_daily_loss_pct - daily_loss:,.0f})"
                )

        # ---- 5. 现金充足性 (买入) ----
        if is_buy and order_value > current_cash:
            return False, f"现金不足: 需要 {order_value:,.0f}, 可用 {current_cash:,.0f}"

        # ---- 全部通过 ----
        return True, "OK"

    # ── 批量校验 ─────────────────────────────────────────

    def check_orders_batch(
        self, orders: List[dict], **kwargs
    ) -> Tuple[List[dict], List[dict]]:
        """
        批量检查订单。

        Returns:
            (通过的订单列表, [{order, reason}] 被拒绝的订单列表)
        """
        passed = []
        rejected = []
        for order in orders:
            ok, reason = self.check_order(order, **kwargs)
            if ok:
                passed.append(order)
            else:
                self._total_rejected += 1
                rejected.append({"order": order, "reason": reason})
                logger.warning(f"[RiskGate] 订单被拦截: {reason}")
        return passed, rejected

    # ── 统计 ─────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        """风控统计"""
        return {
            "total_checks": self._total_checks,
            "total_rejected": self._total_rejected,
            "reject_rate": (
                round(self._total_rejected / max(self._total_checks, 1), 3)
            ),
            "peak_capital": round(self._peak_capital, 2),
            "today_pnl": round(self._today_pnl, 2),
            "daily_loss_pct": (
                round(-self._today_pnl / self._daily_start_capital * 100, 2)
                if self._daily_start_capital > 0 else 0
            ),
        }

    def block_symbol(self, symbol: str):
        """动态添加黑名单"""
        self.blocked_symbols.add(symbol)
        logger.warning(f"[RiskGate] 标的已加入黑名单: {symbol}")

    def unblock_symbol(self, symbol: str):
        """移除黑名单"""
        self.blocked_symbols.discard(symbol)


# ============================================================
# 全局默认闸门 (开箱即用)
# ============================================================

default_gate = PreTradeRiskGate({
    "max_total_position_pct": 0.95,
    "max_single_stock_pct": 0.10,
    "max_daily_loss_pct": 0.05,
    "max_drawdown_pct": 0.20,
    "initial_capital": 1_000_000,
    "max_order_value_pct": 0.30,
})


# ============================================================
# 集成到 PaperBroker 的便捷适配器
# ============================================================

def check_paper_order(
    order: Dict[str, Any],
    broker = None,
    gate: PreTradeRiskGate = None,
) -> Tuple[bool, str]:
    """
    在 PaperBroker.place_order() 中调用的便捷函数。

    自动从 broker 获取当前持仓、总资产、现金，然后调用 gate.check_order()。

    Args:
        order:  订单字典
        broker: PaperBroker 实例 (或兼容接口)
        gate:   PreTradeRiskGate 实例 (默认用 default_gate)

    Returns:
        (通过, 原因)
    """
    gate = gate or default_gate

    # 从 broker 获取当前状态
    positions = {}
    try:
        pos_df = broker.get_positions()
        if pos_df is not None and not pos_df.empty:
            for _, row in pos_df.iterrows():
                sym = str(row.get("symbol", ""))
                qty = float(row.get("quantity", 0))
                price = float(row.get("current_price", row.get("avg_cost", 0)))
                positions[sym] = qty * price
    except Exception:
        pass

    total_value = broker.get_equity() if hasattr(broker, "get_equity") else broker.cash
    cash = broker.cash if hasattr(broker, "cash") else total_value * 0.5

    return gate.check_order(order, positions, total_value, cash)
