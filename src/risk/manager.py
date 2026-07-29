"""
RiskManager — 量化风控引擎 (v5.5)

核心功能:
  1. 移动止损 (Trailing Stop) — 股价从最高点回撤X%触发平仓
  2. 总回撤熔断 (Drawdown Circuit) — 账户峰值回撤超Y%停止开仓
  3. 凯利仓位 (Kelly Criterion) — 根据胜率/盈亏比计算最优仓位
  4. 单股仓位上限 — 不超过总资金15%

用法:
    rm = RiskManager()
    rm.update_price("600498", 35.0)       # 更新持仓价格
    action = rm.check("600498", 35.0)     # 检查是否需要平仓
    ratio = rm.kelly_position(0.5, 2.0)   # 凯利仓位计算
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from datetime import datetime


@dataclass
class PositionRisk:
    """单只持仓的风控状态"""
    symbol: str
    entry_price: float
    highest_price: float
    current_price: float
    trailing_stop_pct: float = 0.05      # 回撤5%触发
    stop_price: float = 0.0
    pnl_pct: float = 0.0

    def update(self, price: float):
        self.current_price = price
        if price > self.highest_price:
            self.highest_price = price
        self.stop_price = self.highest_price * (1 - self.trailing_stop_pct)
        self.pnl_pct = (price / self.entry_price - 1) * 100

    def should_stop(self) -> Tuple[bool, str]:
        """检查是否触发移动止损"""
        if self.current_price <= self.stop_price:
            drawdown = (self.highest_price - self.current_price) / self.highest_price * 100
            return True, f"移动止损: 从最高{self.highest_price:.2f}回撤{drawdown:.1f}%"
        return False, ""


class RiskManager:
    """
    量化风控管理器

    配置参数 (在 config.py 中设置):
        risk_trailing_stop_pct: float = 0.05      # 移动止损回撤比例
        risk_max_drawdown_pct: float = 0.10       # 总回撤熔断线
        risk_max_single_position_pct: float = 0.15 # 单股仓位上限
        risk_kelly_fraction: float = 0.5           # 凯利分数(0.5=半凯利)
        risk_enable_circuit_breaker: bool = True   # 启用熔断
    """

    def __init__(self,
                 initial_capital: float = 100_000,
                 trailing_stop_pct: float = 0.05,
                 max_drawdown_pct: float = 0.10,
                 max_single_pct: float = 0.15,
                 kelly_fraction: float = 0.5,
                 enable_circuit: bool = True):
        self.initial_capital = initial_capital
        self.trailing_stop_pct = trailing_stop_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_single_pct = max_single_pct
        self.kelly_fraction = kelly_fraction
        self.enable_circuit = enable_circuit

        # 账户状态
        self.peak_equity = initial_capital
        self.current_equity = initial_capital
        self.circuit_triggered = False
        self.circuit_reason = ""

        # 持仓风控
        self.positions: Dict[str, PositionRisk] = {}

        # 日志
        self.log: list = []

    # ═══════════════════════════════════════════
    # 1. 移动止损
    # ═══════════════════════════════════════════

    def add_position(self, symbol: str, entry_price: float, stop_pct: float = None):
        """新增持仓, 开始追踪"""
        pct = stop_pct or self.trailing_stop_pct
        self.positions[symbol] = PositionRisk(
            symbol=symbol,
            entry_price=entry_price,
            highest_price=entry_price,
            current_price=entry_price,
            trailing_stop_pct=pct,
        )
        self._log(f"[风控] {symbol} 入场 ¥{entry_price:.2f}, 移动止损 {pct*100:.0f}%")

    def update_price(self, symbol: str, price: float):
        """更新持仓价格"""
        if symbol not in self.positions:
            return
        pos = self.positions[symbol]
        old_high = pos.highest_price
        pos.update(price)
        if pos.highest_price > old_high:
            pos.stop_price = pos.highest_price * (1 - pos.trailing_stop_pct)

    def remove_position(self, symbol: str):
        if symbol in self.positions:
            del self.positions[symbol]

    def check(self, symbol: str, price: float) -> Tuple[bool, str]:
        """
        检查是否触发风控平仓
        返回: (是否平仓, 原因)
        """
        if symbol not in self.positions:
            return False, ""

        self.update_price(symbol, price)
        pos = self.positions[symbol]

        # 移动止损检查
        should_stop, reason = pos.should_stop()
        if should_stop:
            self._log(f"[风控-平仓] {symbol}: {reason}")
            return True, reason

        return False, ""

    def get_stop_price(self, symbol: str) -> float:
        """获取当前止损价"""
        if symbol in self.positions:
            return self.positions[symbol].stop_price
        return 0.0

    # ═══════════════════════════════════════════
    # 2. 总回撤熔断
    # ═══════════════════════════════════════════

    def update_equity(self, equity: float):
        """更新账户权益, 检查熔断"""
        self.current_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity
            if self.circuit_triggered:
                # 权益创新高, 解除熔断
                self.circuit_triggered = False
                self.circuit_reason = ""
                self._log(f"[风控] 熔断解除: 权益创新高 ¥{equity:,.0f}")

        # 检查回撤
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity
            if self.enable_circuit and drawdown >= self.max_drawdown_pct:
                if not self.circuit_triggered:
                    self.circuit_triggered = True
                    self.circuit_reason = (f"回撤熔断: 峰值¥{self.peak_equity:,.0f}→¥{equity:,.0f}"
                                           f" ({drawdown*100:.1f}%)")
                    self._log(f"[风控-熔断] {self.circuit_reason}")

    def can_open_new(self) -> Tuple[bool, str]:
        """是否可以开新仓"""
        if self.circuit_triggered:
            return False, f"熔断中: {self.circuit_reason}"
        return True, ""

    def get_drawdown(self) -> float:
        """当前回撤比例"""
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity

    # ═══════════════════════════════════════════
    # 3. 凯利公式仓位计算
    # ═══════════════════════════════════════════

    def kelly_position(self, win_rate: float, profit_loss_ratio: float,
                       capital: float = None) -> dict:
        """
        凯利公式: f* = (p*b - q) / b
          p = 胜率, b = 盈亏比, q = 1-p

        返回:
          kelly_raw: 原始凯利比例
          kelly_half: 半凯利比例
          recommended_pct: 建议仓位%(考虑上限)
          recommended_amount: 建议金额
          max_shares: 建议股数(整数手)
        """
        cap = capital or self.current_equity
        q = 1 - win_rate

        if profit_loss_ratio <= 0 or win_rate <= 0:
            return {"kelly_raw": 0, "kelly_half": 0, "recommended_pct": 0,
                    "recommended_amount": 0, "max_shares": 0, "warning": "胜率/盈亏比无效"}

        # 原始凯利
        kelly_raw = (win_rate * profit_loss_ratio - q) / profit_loss_ratio
        kelly_raw = max(0, min(kelly_raw, 1.0))

        # 半凯利 (更保守)
        kelly_half = kelly_raw * self.kelly_fraction

        # 应用上限
        recommended_pct = min(kelly_half, self.max_single_pct)
        recommended_amount = cap * recommended_pct

        return {
            "kelly_raw": round(kelly_raw * 100, 1),
            "kelly_half": round(kelly_half * 100, 1),
            "recommended_pct": round(recommended_pct * 100, 1),
            "recommended_amount": round(recommended_amount, 0),
            "max_shares": int(recommended_amount / 100) * 100 if recommended_amount > 0 else 0,
        }

    # ═══════════════════════════════════════════
    # 4. 综合风控报告
    # ═══════════════════════════════════════════

    def report(self) -> str:
        """生成风控报告"""
        lines = []
        lines.append("═══ 风控报告 ═══")
        lines.append(f"权益: ¥{self.current_equity:,.0f} | 峰值: ¥{self.peak_equity:,.0f}")
        lines.append(f"回撤: {self.get_drawdown()*100:.1f}% | 熔断: {'是' if self.circuit_triggered else '否'}")
        lines.append("")
        if self.positions:
            lines.append(f"持仓风控 ({len(self.positions)}只):")
            for sym, pos in self.positions.items():
                drawdown = (pos.highest_price - pos.current_price) / pos.highest_price * 100 if pos.highest_price > 0 else 0
                lines.append(f"  {sym}: ¥{pos.current_price:.2f} | "
                           f"最高¥{pos.highest_price:.2f} | "
                           f"止损¥{pos.stop_price:.2f} | "
                           f"回撤{drawdown:.1f}% | "
                           f"盈亏{pos.pnl_pct:+.1f}%")
        else:
            lines.append("无持仓")
        return "\n".join(lines)

    def _log(self, msg: str):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def get_recent_logs(self, n: int = 20) -> list:
        return self.log[-n:]
