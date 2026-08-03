"""
策略相关数据模型

- Signal：策略产生的交易信号
- StrategyConfig：策略参数配置
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Signal:
    """一条交易信号 (v7.0: 新增 reason_code)"""
    action: str            # "BUY" / "SELL" / "SHORT" / "COVER" / "HOLD"
    symbol: str            # 股票代码
    date: str              # 信号日期 YYYY-MM-DD
    price: float           # 触发价格
    quantity: int = 0      # 建议数量
    reason: str = ""       # 信号理由(人类可读)
    reason_code: str = ""  # 决策原因码 (如 REASON_RSI_OVERSOLD)
    confidence: float = 1.0  # 信号置信度 0-1

    @property
    def is_buy(self) -> bool:
        return self.action == "BUY"

    @property
    def is_sell(self) -> bool:
        return self.action == "SELL"

    @property
    def is_short(self) -> bool:
        return self.action == "SHORT"

    @property
    def is_cover(self) -> bool:
        return self.action == "COVER"


@dataclass
class StrategyConfig:
    """策略参数配置"""
    name: str = ""                 # 策略名称
    initial_capital: float = 100_000  # 初始资金
    position_size_pct: float = 0.2   # 单笔仓位占比
    max_positions: int = 10          # 最大持仓数
    stop_loss_pct: float = 0.05      # 止损比例
    take_profit_pct: float = 0.15    # 止盈比例
    commission_rate: float = 0.0003  # 手续费率
    slippage: float = 0.001          # 滑点

    def __post_init__(self):
        if self.name == "":
            self.name = "默认策略"

    def to_v2_parameters(self) -> dict[str, float | int]:
        """Expose execution settings without coupling legacy code to V2 internals."""
        return {
            "initial_capital": self.initial_capital,
            "position_size_pct": self.position_size_pct,
            "max_positions": self.max_positions,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "commission_rate": self.commission_rate,
            "slippage": self.slippage,
        }
