"""
回测引擎 — 事件驱动，逐日遍历历史数据

流程：
1. 加载行情数据
2. 逐日遍历，调用策略的 on_bar 获取信号
3. 模拟成交（含手续费、滑点）
4. 记录每笔模拟交易的完整生命周期
"""

import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
from src.models.strategy import Signal


class Portfolio:
    """模拟账户"""

    def __init__(self, initial_capital: float = 100_000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, dict] = {}     # symbol -> {qty, avg_cost}
        self.trade_log: List[dict] = []           # 交易记录
        self.daily_values: List[dict] = []        # 每日净值

    @property
    def total_value(self) -> float:
        """当前总资产（现金 + 多头市值 - 空头市值）"""
        long_value = 0
        short_liability = 0
        for key, p in self.positions.items():
            px = p.get("last_price", p["avg_cost"])
            if key.startswith("SHORT_"):
                short_liability += p["qty"] * px  # 欠的股票市值
            else:
                long_value += p["qty"] * px
        return self.cash + long_value - short_liability

    def buy(self, symbol: str, price: float, quantity: int,
            date: str, commission_rate: float = 0.0003):
        """买入"""
        cost = price * quantity
        fee = cost * commission_rate
        total_cost = cost + fee

        if total_cost > self.cash:
            # 资金不足，按可买数量调整
            affordable_qty = int(self.cash / (price * (1 + commission_rate)))
            if affordable_qty <= 0:
                return None
            quantity = affordable_qty
            cost = price * quantity
            fee = cost * commission_rate
            total_cost = cost + fee

        self.cash -= total_cost

        if symbol not in self.positions:
            self.positions[symbol] = {"qty": 0, "avg_cost": 0}

        # 更新持仓
        old_qty = self.positions[symbol]["qty"]
        old_cost = self.positions[symbol]["avg_cost"]
        new_qty = old_qty + quantity
        new_avg_cost = (old_cost * old_qty + cost) / new_qty if new_qty > 0 else 0
        self.positions[symbol] = {"qty": new_qty, "avg_cost": new_avg_cost, "last_price": price}

        record = {
            "date": date, "symbol": symbol, "action": "BUY",
            "price": price, "quantity": quantity, "fee": round(fee, 2),
            "cost": round(cost, 2), "cash_after": round(self.cash, 2),
        }
        self.trade_log.append(record)
        return record

    def sell(self, symbol: str, price: float, quantity: int,
             date: str, commission_rate: float = 0.0003):
        """卖出"""
        if symbol not in self.positions or self.positions[symbol]["qty"] <= 0:
            return None

        qty = min(quantity, self.positions[symbol]["qty"])
        proceeds = price * qty
        fee = proceeds * commission_rate
        net_proceeds = proceeds - fee

        # 计算盈亏
        avg_cost = self.positions[symbol]["avg_cost"]
        pnl = (price - avg_cost) * qty - fee

        self.cash += net_proceeds
        self.positions[symbol]["qty"] -= qty
        self.positions[symbol]["last_price"] = price

        if self.positions[symbol]["qty"] <= 0:
            del self.positions[symbol]

        record = {
            "date": date, "symbol": symbol, "action": "SELL",
            "price": price, "quantity": qty, "fee": round(fee, 2),
            "proceeds": round(net_proceeds, 2), "pnl": round(pnl, 2),
            "cash_after": round(self.cash, 2),
        }
        self.trade_log.append(record)
        return record

    def short(self, symbol: str, price: float, quantity: int,
             date: str, commission_rate: float = 0.0003):
        """做空"""
        cost = price * quantity
        fee = cost * commission_rate

        if cost + fee > self.cash:
            affordable = int(self.cash / (price * (1 + commission_rate)))
            if affordable <= 0: return None
            quantity = affordable
            cost = price * quantity
            fee = cost * commission_rate

        self.cash -= fee  # 只扣手续费，做空获得现金
        self.cash += cost  # 卖出获得现金

        short_key = "SHORT_" + symbol
        self.positions[short_key] = {"qty": quantity, "avg_cost": price, "last_price": price}

        record = {"date": date, "symbol": symbol, "action": "SHORT",
                  "price": price, "quantity": quantity, "fee": round(fee, 2),
                  "cash_after": round(self.cash, 2)}
        self.trade_log.append(record)
        return record

    def cover_short(self, symbol: str, price: float, quantity: int,
                   date: str, commission_rate: float = 0.0003):
        """平空"""
        short_key = "SHORT_" + symbol
        if short_key not in self.positions: return None

        qty = min(quantity, self.positions[short_key]["qty"])
        cost = price * qty
        fee = cost * commission_rate
        total_cost = cost + fee

        if total_cost > self.cash:
            qty = int(self.cash / (price * (1 + commission_rate)))
            if qty <= 0: return None
            cost = price * qty
            fee = cost * commission_rate
            total_cost = cost + fee

        self.cash -= total_cost

        entry_price = self.positions[short_key]["avg_cost"]
        pnl = (entry_price - price) * qty - fee  # 做空: 跌了赚钱

        self.positions[short_key]["qty"] -= qty
        if self.positions[short_key]["qty"] <= 0:
            del self.positions[short_key]

        record = {"date": date, "symbol": symbol, "action": "COVER",
                  "price": price, "quantity": qty, "fee": round(fee, 2),
                  "pnl": round(pnl, 2), "cash_after": round(self.cash, 2)}
        self.trade_log.append(record)
        return record

    def mark_to_market(self, date: str, prices: dict):
        """按市价估值，记录每日净值"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol]["last_price"] = price
            short_key = "SHORT_" + symbol
            if short_key in self.positions:
                self.positions[short_key]["last_price"] = price

        long_val = sum(
            p["qty"] * p.get("last_price", p["avg_cost"])
            for k, p in self.positions.items() if not k.startswith("SHORT_")
        )
        short_val = sum(
            p["qty"] * p.get("last_price", p["avg_cost"])
            for k, p in self.positions.items() if k.startswith("SHORT_")
        )

        self.daily_values.append({
            "date": date,
            "cash": round(self.cash, 2),
            "position_value": round(long_val - short_val, 2),
            "total_value": round(self.total_value, 2),
        })


class BacktestEngine:
    """事件驱动回测引擎"""

    def __init__(self,
                 initial_capital: float = 100_000,
                 commission_rate: float = 0.0003,
                 slippage: float = 0.001,
                 use_market_filter: bool = False):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.use_market_filter = use_market_filter
        self.portfolio = Portfolio(initial_capital)

    def run(self, strategy, data: pd.DataFrame,
            position_size_pct: float = 0.2) -> dict:
        """
        执行回测

        参数:
            strategy: 策略对象（需实现 on_bar 方法）
            data: OHLCV DataFrame（需包含 date, open, high, low, close, volume 列）
            position_size_pct: 单笔仓位占比

        返回:
            dict: {
                "portfolio": Portfolio 对象,
                "signals": 产生的信号列表,
                "metrics": 绩效指标字典,
            }
        """
        self.portfolio = Portfolio(self.initial_capital)
        signals_log = []

        data = data.sort_values("date").reset_index(drop=True)

        for i in range(len(data)):
            row = data.iloc[i]
            date = str(row["date"])[:10]

            # 构建历史切片（到当前行为止）
            bar_data = data.iloc[:i + 1].copy()

            # 调用策略
            signal = strategy.on_bar(i, bar_data, self.portfolio)

            if signal is None:
                # 按市价估值
                prices = {row.get("symbol", ""): row["close"]}
                self.portfolio.mark_to_market(date, prices)
                continue

            if not isinstance(signal, Signal):
                signals_log.append(signal)
                continue

            # === 多因子择时过滤 (v4.4) ===
            if self.use_market_filter and signal.action == "BUY":
                if i >= 60:
                    from src.factors.definitions import FactorCalculator
                    try:
                        calc = FactorCalculator(bar_data)
                        f = calc.compute_all().iloc[-1]
                        slope = float(f.get("ma_slope", 0.5))
                        align = float(f.get("ma_alignment", 0.5))
                        position = float(f.get("price_position", 0.5))
                        regime_score = (slope + align + position) / 3

                        if regime_score < 0.4:
                            signals_log.append({
                                "date": date, "action": "SKIP",
                                "symbol": signal.symbol, "price": signal.price,
                                "reason": f"多因子择时(熊市): score={regime_score:.2f}",
                            })
                            prices = {row.get("symbol", ""): row["close"]}
                            self.portfolio.mark_to_market(date, prices)
                            continue
                    except Exception:
                        pass  # 因子计算失败则不过滤
            # ==========================

            signals_log.append({
                "date": date, "action": signal.action,
                "symbol": signal.symbol, "price": signal.price,
                "reason": signal.reason,
            })

            # 执行信号
            exec_price = row["close"] * (1 + self.slippage) if signal.action == "BUY" \
                else row["close"] * (1 - self.slippage)

            if signal.action == "BUY":
                # 先平空头(如有)
                short_key = "SHORT_" + signal.symbol
                if short_key in self.portfolio.positions:
                    qty = self.portfolio.positions[short_key]["qty"]
                    self.portfolio.cover_short(
                        signal.symbol, exec_price, qty, date, self.commission_rate)
                # 开多头
                max_cost = self.portfolio.total_value * position_size_pct
                qty = signal.quantity if signal.quantity > 0 else \
                    int(max_cost / exec_price / 100) * 100
                if qty > 0:
                    self.portfolio.buy(
                        signal.symbol, exec_price, qty, date, self.commission_rate)

            elif signal.action == "SELL":
                if signal.symbol in self.portfolio.positions:
                    qty = signal.quantity if signal.quantity > 0 else \
                        self.portfolio.positions[signal.symbol]["qty"]
                    self.portfolio.sell(
                        signal.symbol, exec_price, qty, date, self.commission_rate)

            elif signal.action == "SHORT":
                # 先平多头(如有)
                if signal.symbol in self.portfolio.positions:
                    qty = self.portfolio.positions[signal.symbol]["qty"]
                    self.portfolio.sell(
                        signal.symbol, exec_price, qty, date, self.commission_rate)
                # 开空头
                max_cost = self.portfolio.total_value * position_size_pct
                qty = signal.quantity if signal.quantity > 0 else \
                    int(max_cost / exec_price / 100) * 100
                if qty > 0:
                    self.portfolio.short(
                        signal.symbol, exec_price, qty, date, self.commission_rate)

            elif signal.action == "COVER":
                short_key = "SHORT_" + signal.symbol
                if short_key in self.portfolio.positions:
                    qty = signal.quantity if signal.quantity > 0 else \
                        self.portfolio.positions[short_key]["qty"]
                    self.portfolio.cover_short(
                        signal.symbol, exec_price, qty, date, self.commission_rate)

            # 每日估值
            prices = {signal.symbol: row["close"]}
            self.portfolio.mark_to_market(date, prices)

        # 计算绩效指标
        metrics = self._calc_metrics()

        return {
            "portfolio": self.portfolio,
            "signals": signals_log,
            "metrics": metrics,
        }

    def _calc_metrics(self) -> dict:
        """从 portfolio.daily_values 计算绩效指标"""
        from src.backtest.metrics import calc_all_metrics
        return calc_all_metrics(
            self.portfolio.daily_values,
            self.portfolio.trade_log,
            self.initial_capital,
        )
