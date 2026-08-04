"""
ExecutionEngine — 专业订单执行引擎 (v7.1)

1. 冰山订单: 大单自动拆分, Poisson随机间隔, 隐藏意图
2. 盘口追踪: 模拟Level2十档, 动态调整买入量
3. 撤单重发: 30秒未成交自动撤单, 记录摩擦成本
"""

import random
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import deque


@dataclass
class OrderSlice:
    """一笔订单切片"""
    id: str
    price: float
    quantity: int
    filled: int = 0
    status: str = "pending"  # pending/partial/filled/cancelled
    created_at: float = 0.0
    cancelled_at: float = 0.0


@dataclass
class OrderBook:
    """模拟十档盘口 (从OHLCV重建)"""
    bid_prices: List[float] = field(default_factory=list)   # 买一到买五
    bid_volumes: List[int] = field(default_factory=list)
    ask_prices: List[float] = field(default_factory=list)   # 卖一到卖五
    ask_volumes: List[int] = field(default_factory=list)
    spread: float = 0.0
    mid_price: float = 0.0

    @property
    def total_ask_volume(self) -> int:
        """卖一到卖五总挂单量"""
        return sum(self.ask_volumes[:5]) if self.ask_volumes else 0

    @property
    def weighted_ask_price(self) -> float:
        """量加权卖价 (买入成本)"""
        if not self.ask_volumes or sum(self.ask_volumes[:5]) == 0:
            return self.ask_prices[0] if self.ask_prices else 0
        total = sum(self.ask_volumes[:5])
        return sum(p * v for p, v in zip(self.ask_prices[:5], self.ask_volumes[:5])) / total


def simulate_orderbook(close: float, high: float, low: float,
                       volume: int, tick_size: float = 0.01) -> OrderBook:
    """
    从日线数据模拟十档盘口
    """
    ob = OrderBook()
    spread_pct = random.uniform(0.0002, 0.002)
    spread = max(tick_size, close * spread_pct)
    mid = close
    ob.mid_price = mid
    ob.spread = spread

    # 卖盘 (ask): mid → high
    daily_range = high - low
    if daily_range <= 0:
        daily_range = close * 0.02

    for level in range(5):
        ask_px = mid + spread / 2 + (daily_range * 0.02 * (level + 1))
        ask_vol = max(100, int(volume * 0.02 * (5 - level) / 5 / 100) * 100)
        ob.ask_prices.append(round(ask_px, 3))
        ob.ask_volumes.append(ask_vol)

    # 买盘 (bid): mid - spread → low
    for level in range(5):
        bid_px = mid - spread / 2 - (daily_range * 0.02 * (level + 1))
        bid_vol = max(100, int(volume * 0.02 * (5 - level) / 5 / 100) * 100)
        ob.bid_prices.append(round(bid_px, 3))
        ob.bid_volumes.append(bid_vol)

    return ob


class ExecutionEngine:
    """Legacy experimental adapter; new paper accounts use the V2 PaperBroker."""

    def __init__(self):
        # 成交统计
        self.total_submitted = 0
        self.total_filled = 0
        self.total_cancelled = 0
        self.total_slices = 0
        # 摩擦成本
        self.slippage_cost = 0.0
        self.cancel_cost = 0.0
        # 执行日志
        self._log: deque = deque(maxlen=200)

    # ═══════════════════════════════════════════
    # 1. 冰山订单
    # ═══════════════════════════════════════════

    def iceberg_split(self, total_qty: int, avg_daily_volume: int,
                      min_slices: int = 5, max_slices: int = 10,
                      threshold_pct: float = 0.05) -> List[OrderSlice]:
        """
        冰山订单拆分

        total_qty:        总买入量
        avg_daily_volume: 近20日日均成交量
        threshold_pct:    超过成交量此比例则拆分
        """
        order_pct = total_qty / avg_daily_volume if avg_daily_volume > 0 else 1.0

        if order_pct < threshold_pct:
            # 小单不拆分
            return [OrderSlice(
                id=f"ICE_1", price=0.0, quantity=total_qty,
                status="pending", created_at=time.time()
            )]

        # 拆分
        n_slices = random.randint(min_slices, max_slices)
        # 非均匀拆分: 第一笔小,逐渐增大(不引起注意)
        weights = [1.0 + i * 0.3 for i in range(n_slices)]
        total_w = sum(weights)

        slices = []
        remaining = total_qty
        for i in range(n_slices):
            if i == n_slices - 1:
                qty = remaining
            else:
                qty = max(100, int(total_qty * weights[i] / total_w / 100) * 100)
            remaining -= qty
            sl = OrderSlice(
                id=f"ICE_{i+1}/{n_slices}",
                price=0.0,
                quantity=qty,
                status="pending",
                created_at=time.time(),
            )
            slices.append(sl)

        self.total_slices += len(slices)
        self._log.append(f"[Iceberg] {total_qty}股→{n_slices}笔 "
                        f"({order_pct*100:.1f}%日均量)")
        return slices

    def poisson_interval(self, mean_seconds: float = 30.0) -> float:
        """Poisson分布随机间隔"""
        return max(5.0, random.expovariate(1.0 / mean_seconds))

    # ═══════════════════════════════════════════
    # 2. 盘口动态追踪
    # ═══════════════════════════════════════════

    def check_depth(self, order_qty: int, orderbook: OrderBook) -> Tuple[int, float, str]:
        """
        检查盘口深度, 动态调整买入量

        返回: (adjusted_qty, estimated_cost, reason)
        """
        total_ask_vol = orderbook.total_ask_volume
        weighted_price = orderbook.weighted_ask_price

        if total_ask_vol == 0:
            return order_qty, weighted_price, "无盘口数据,原量执行"

        # 挂单量 = 订单量的50%~200% → 按实际深度调整
        fill_ratio = total_ask_vol / order_qty if order_qty > 0 else 1.0

        if fill_ratio >= 2.0:
            # 盘口远大于需求 → 正常执行
            return order_qty, weighted_price, f"盘口充足({fill_ratio:.1f}x)"

        elif fill_ratio >= 1.0:
            # 刚好够 → 全量执行
            return order_qty, weighted_price, f"盘口刚好({fill_ratio:.1f}x)"

        elif fill_ratio >= 0.5:
            # 不太够 → 减量到80%
            adjusted = int(order_qty * 0.8 / 100) * 100
            return max(100, adjusted), weighted_price, f"盘口不足({fill_ratio:.1f}x),减量20%"

        else:
            # 严重不足 → 只买盘口量的80%
            adjusted = int(total_ask_vol * 0.8 / 100) * 100
            return max(100, adjusted), weighted_price, f"盘口严重不足({fill_ratio:.1f}x),减量到{adjusted}股"

    # ═══════════════════════════════════════════
    # 3. 撤单重发
    # ═══════════════════════════════════════════

    def cancel_and_replace(self, slice_: OrderSlice,
                           new_orderbook: OrderBook,
                           timeout: float = 30.0) -> Tuple[Optional[OrderSlice], str]:
        """
        限价单超时撤单重发

        返回: (新订单或None, 原因)
        """
        elapsed = time.time() - slice_.created_at

        if slice_.status != "pending":
            return None, "订单已完成"

        if elapsed < timeout:
            return slice_, f"等待中({elapsed:.1f}s/{timeout}s)"

        # 超时 → 撤单
        slice_.status = "cancelled"
        slice_.cancelled_at = time.time()
        self.total_cancelled += 1
        self.cancel_cost += slice_.quantity * 0.001  # 撤单摩擦成本

        # 重发: 用新的买一价
        new_bid = new_orderbook.bid_prices[0] if new_orderbook.bid_prices else slice_.price
        new_slice = OrderSlice(
            id=f"{slice_.id}_R",
            price=new_bid,
            quantity=slice_.quantity - slice_.filled,
            status="pending",
            created_at=time.time(),
        )

        reason = (f"超时撤单({elapsed:.0f}s) → 重新挂单 "
                  f"@{new_bid:.3f} x{new_slice.quantity}")
        self._log.append(f"[CancelReplace] {reason}")
        return new_slice, reason

    # ═══════════════════════════════════════════
    # 4. 完整执行流程
    # ═══════════════════════════════════════════

    def execute_buy(self, symbol: str, total_qty: int,
                    data: "pd.DataFrame",
                    position_size_pct: float = 0.2,
                    portfolio_value: float = 100_000) -> Dict:
        """
        完整的买入执行流程

        返回: {
          filled_qty, avg_price, total_cost, slices_executed,
          cancel_count, iceberg_used, impact_estimate_pct
        }
        """
        import pandas as pd

        close = float(data["close"].iloc[-1])
        high = float(data["high"].iloc[-1])
        low = float(data["low"].iloc[-1])
        volume = int(data["volume"].iloc[-1])

        # 日均成交量
        avg_vol = int(data["volume"].rolling(20).mean().iloc[-1]) if len(data) >= 20 else volume

        # 1. 冰山拆分
        slices = self.iceberg_split(total_qty, avg_vol)
        iceberg_used = len(slices) > 1

        # 2. 模拟盘口
        orderbook = simulate_orderbook(close, high, low, volume)

        # 3. 逐片执行
        slices_executed = []
        total_filled = 0
        total_cost = 0.0
        cancel_count = 0
        prev_time = time.time()

        for i, sl in enumerate(slices):
            # Poisson间隔 (非首片)
            if i > 0:
                delay = self.poisson_interval(20.0)
                time.sleep(min(delay * 0.001, 0.1))

            # 刷新盘口 (每次执行前)
            ob = simulate_orderbook(
                close * random.uniform(0.998, 1.002),
                high, low, volume,
            )

            # 检查深度
            adjusted_qty, est_price, depth_reason = self.check_depth(sl.quantity, ob)

            # 撤单重发检查
            if sl.status == "pending" and time.time() - sl.created_at > 30:
                new_sl, reason = self.cancel_and_replace(sl, ob, 30)
                if new_sl and new_sl != sl:
                    cancel_count += 1
                    sl = new_sl
                    adjusted_qty = min(adjusted_qty, sl.quantity)

            # 模拟成交
            fill_rate = random.uniform(0.7, 1.0)
            filled = int(adjusted_qty * fill_rate / 100) * 100
            filled = min(filled, adjusted_qty)

            if filled > 0:
                exec_price = est_price * random.uniform(0.999, 1.002)
                cost = exec_price * filled
                total_filled += filled
                total_cost += cost
                sl.filled = filled
                sl.status = "filled"
                sl.price = round(exec_price, 3)

            slices_executed.append({
                "slice_id": sl.id,
                "quantity": adjusted_qty,
                "filled": sl.filled,
                "price": round(sl.price, 3),
                "status": sl.status,
                "time": round(time.time() - prev_time, 3),
            })
            prev_time = time.time()

        self.total_submitted += total_qty
        self.total_filled += total_filled

        avg_price = total_cost / total_filled if total_filled > 0 else close
        impact_bps = (avg_price / close - 1) * 10000

        return {
            "symbol": symbol,
            "submitted_qty": total_qty,
            "filled_qty": total_filled,
            "avg_price": round(avg_price, 3),
            "total_cost": round(total_cost, 2),
            "slices_executed": slices_executed,
            "iceberg_slices": len(slices),
            "iceberg_used": iceberg_used,
            "cancel_count": cancel_count,
            "impact_bps": round(impact_bps, 1),
            "depth_checks_passed": len(slices_executed),
            "log": list(self._log)[-5:],
        }

    def execute_sell(self, symbol: str, total_qty: int,
                     data: "pd.DataFrame") -> Dict:
        """卖出执行 (类似买入, 方向相反)"""
        result = self.execute_buy(symbol, total_qty, data)
        result["side"] = "SELL"
        return result

    # ═══════════════════════════════════════════
    # 5. 统计
    # ═══════════════════════════════════════════

    def stats(self) -> dict:
        fills = self.total_filled
        submits = self.total_submitted
        return {
            "fill_rate": round(fills / max(submits, 1) * 100, 1),
            "cancel_rate": round(self.total_cancelled / max(submits, 1) * 100, 1),
            "total_submitted": submits,
            "total_filled": fills,
            "total_cancelled": self.total_cancelled,
            "total_slices": self.total_slices,
            "slippage_cost_bps": round(self.slippage_cost / max(fills, 1) * 10000, 1),
            "cancel_cost_bps": round(self.cancel_cost / max(fills, 1) * 10000, 1),
        }

    def report(self) -> str:
        s = self.stats()
        return (f"═══ Execution Stats ═══\n"
                f"提交: {s['total_submitted']} | "
                f"成交: {s['total_filled']} ({s['fill_rate']}%) | "
                f"撤单: {s['total_cancelled']} ({s['cancel_rate']}%)\n"
                f"冰山切片: {s['total_slices']} | "
                f"冲击成本: {s['slippage_cost_bps']}bps | "
                f"撤单摩擦: {s['cancel_cost_bps']}bps")


# 全局实例
exec_engine = ExecutionEngine()
