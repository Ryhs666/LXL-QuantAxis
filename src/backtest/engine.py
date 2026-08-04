"""
回测引擎 — 事件驱动，逐日遍历历史数据

流程：
1. 加载行情数据
2. 逐日遍历，调用策略的 on_bar 获取信号
3. 模拟成交（含手续费、滑点）
4. 记录每笔模拟交易的完整生命周期
"""

import os

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

    def to_immutable_ledger(self, currency: str = "CNY"):
        """Replay legacy long fills into the V2 append-only accounting ledger."""
        from decimal import Decimal

        from src.lxl_quantaxis.portfolio import FillSide, PortfolioLedger, TradeFill

        ledger = PortfolioLedger(Decimal(str(self.initial_capital)), currency)
        for index, trade in enumerate(self.trade_log):
            action = trade.get("action")
            if action not in {"BUY", "SELL"}:
                raise ValueError("legacy short trades require the future margin-ledger adapter")
            ledger = ledger.post_fill(TradeFill(
                fill_id=f"legacy-{index}",
                executed_at=datetime.fromisoformat(str(trade["date"])),
                symbol=str(trade["symbol"]),
                side=FillSide.BUY if action == "BUY" else FillSide.SELL,
                quantity=int(trade["quantity"]),
                price=Decimal(str(trade["price"])),
                fee=Decimal(str(trade.get("fee", 0))),
                currency=currency,
            ))
        return ledger


class BacktestEngine:
    """事件驱动回测引擎"""

    def __init__(self,
                 initial_capital: float = 100_000,
                 commission_rate: float = 0.0003,
                 slippage: float = 0.001,
                 use_market_filter: bool = False,
                 use_risk_manager: bool = True,
                 # 微观结构 (v6.6)
                 use_impact_cost: bool = True,
                 use_limit_order: bool = False,
                 impact_coefficient: float = 0.1,
                 token_validator=None,
                 legacy_backtest_mode: bool = None,
                 random_seed: int = 0,
                 fill_model=None,
                 risk_policy_chain=None):  # 陷阱4: Token过期检查回调
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.use_market_filter = use_market_filter
        self.use_risk_manager = use_risk_manager
        self.use_impact_cost = use_impact_cost
        self.use_limit_order = use_limit_order
        self.impact_coefficient = impact_coefficient
        self.portfolio = Portfolio(initial_capital)
        # 风控管理器
        self.risk = None
        if use_risk_manager:
            from src.risk.manager import RiskManager
            self.risk = RiskManager(initial_capital=initial_capital)
        self.token_validator = token_validator  # 陷阱4
        if legacy_backtest_mode is None:
            legacy_backtest_mode = os.environ.get("LEGACY_BACKTEST_MODE", "").strip().lower() in {
                "1", "true", "yes", "on"
            }
        self.legacy_backtest_mode = legacy_backtest_mode
        self.random_seed = random_seed
        self.fill_model = fill_model
        self.risk_policy_chain = risk_policy_chain
        self._risk_signals = []  # 风控产生的信号记录
        self._fill_stats = {"attempted": 0, "filled": 0, "cancelled": 0}

    @staticmethod
    def _resolve_symbol(strategy, data: pd.DataFrame) -> str:
        """Resolve the trading symbol from strategy config, data attrs, or
        the 'symbol' column if present.

        Priority:
          1. strategy.config.name (explicit)
          2. data.attrs['symbol'] (from get_data attrs)
          3. data['symbol'].iloc[0] if column exists
          4. "" — caller must handle empty symbol in valuation
        """
        if hasattr(strategy, 'config') and strategy.config and strategy.config.name:
            return str(strategy.config.name)
        if hasattr(data, 'attrs') and 'symbol' in data.attrs:
            return str(data.attrs['symbol'])
        if 'symbol' in data.columns and len(data) > 0:
            return str(data['symbol'].iloc[0])
        return ""  # legacy: caller handles empty

    def run(self, strategy, data: pd.DataFrame,
            position_size_pct: float = 0.2) -> dict:
        """Run with next-bar fills by default; legacy semantics are comparison-only."""
        if self.legacy_backtest_mode:
            return self._run_legacy(strategy, data, position_size_pct)
        return self._run_next_bar(strategy, data, position_size_pct)

    def _run_legacy(self, strategy, data: pd.DataFrame,
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
        # 审计日志
        from src.audit.TradeAudit import audit

        self.portfolio = Portfolio(self.initial_capital)
        signals_log = []
        symbol = self._resolve_symbol(strategy, data)

        data = data.sort_values("date").reset_index(drop=True)

        for i in range(len(data)):
            # 陷阱4: 每100根bar检查一次token是否过期
            if self.token_validator and i % 100 == 0:
                try:
                    self.token_validator()
                except Exception:
                    raise  # SessionExpired 直接抛出中断回测

            row = data.iloc[i]
            date = str(row["date"])[:10]

            # 构建历史切片（到当前行为止）
            bar_data = data.iloc[:i + 1].copy()

            # 调用策略
            signal = strategy.on_bar(i, bar_data, self.portfolio)

            if signal is None:
                # 按市价估值
                prices = {symbol: row["close"]}
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
                            prices = {symbol: row["close"]}
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

            # 执行信号 — 微观结构模拟 (v6.6)
            base_price = row["close"]

            # 1. 冲击成本
            impact_cost = 0.0
            if self.use_impact_cost and signal.action in ("BUY", "SELL"):
                daily_vol = row.get("volume", 1)
                if daily_vol > 0:
                    order_ratio = (signal.price * max(signal.quantity, 1)) / (base_price * daily_vol)
                    if order_ratio > 0.01:  # 超过成交量1%开始计算冲击
                        impact_cost = self.impact_coefficient * order_ratio

            # 2. 限价单模拟
            fill_price = base_price
            filled = True
            if self.use_limit_order and signal.action == "BUY":
                self._fill_stats["attempted"] += 1
                # 模拟排队: 随机0~100, 低于70表示成交
                queue_pos = __import__('random').randint(0, 100)
                if queue_pos < 70:
                    # 成交: 买一价(略低于收盘价)
                    spread = base_price * __import__('random').uniform(0.0001, 0.001)
                    fill_price = base_price - spread
                    self._fill_stats["filled"] += 1
                else:
                    filled = False
                    self._fill_stats["cancelled"] += 1

            if not filled:
                prices = {signal.symbol: row["close"]}
                self.portfolio.mark_to_market(date, prices)
                continue

            # 最终执行价 = 基础价 + 滑点 + 冲击成本
            exec_price = fill_price
            if signal.action == "BUY":
                exec_price = fill_price * (1 + self.slippage + impact_cost)
            else:
                exec_price = fill_price * (1 - self.slippage - impact_cost)

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

            # 审计记录
            try:
                qty = signal.quantity if signal.quantity > 0 else 0
                audit.log_decision(
                    action=signal.action, symbol=signal.symbol,
                    price=signal.price, quantity=qty,
                    strategy=strategy.__class__.__name__ if 'strategy' in dir() else "",
                    reason=signal.reason,
                    portfolio_value=self.portfolio.total_value,
                )
            except:
                pass

            # 每日估值
            prices = {signal.symbol: row["close"]}
            self.portfolio.mark_to_market(date, prices)

            # === 风控检查 (v5.5) ===
            if self.risk:
                self.risk.update_equity(self.portfolio.total_value)
                # 检查是否需要熔断跳过多头买入
                if signal.action == "BUY" and self.risk.circuit_triggered:
                    self._risk_signals.append({
                        "date": date, "action": "RISK_SKIP",
                        "reason": f"熔断: {self.risk.circuit_reason}"
                    })

        # 计算绩效指标
        metrics = self._calc_metrics()

        result = {
            "portfolio": self.portfolio,
            "signals": signals_log,
            "metrics": metrics,
        }
        if self.risk:
            result["risk_report"] = self.risk.report()
            result["risk_logs"] = self.risk.get_recent_logs(20)
            result["risk_signals"] = self._risk_signals
        return result

    def _run_next_bar(self, strategy, data: pd.DataFrame,
                      position_size_pct: float = 0.2) -> dict:
        """Run point-in-time bars and execute close-derived signals next open."""
        from src.audit.TradeAudit import audit
        from src.lxl_quantaxis.backtest import BacktestEventLoop, DataPortal
        from src.lxl_quantaxis.backtest.execution.fill_models import NextBarOpenFillModel

        self.portfolio = Portfolio(self.initial_capital)
        self._risk_signals = []
        resolved_symbol = self._resolve_symbol(strategy, data)
        portal = DataPortal(data)
        event_loop = BacktestEventLoop(portal)
        fill_model = self.fill_model or NextBarOpenFillModel(
            slippage=self.slippage,
            use_impact_cost=self.use_impact_cost,
            impact_coefficient=self.impact_coefficient,
            use_limit_order=self.use_limit_order,
            random_seed=self.random_seed,
        )
        signals_log = []
        risk_decisions = []

        for bar in event_loop.bars():
            i = bar.index
            row = bar.row
            date = str(row["date"])[:10]
            if self.token_validator and i % 100 == 0:
                self.token_validator()

            filled_actions = []
            for scheduled in event_loop.due(i):
                fill = fill_model.fill(scheduled, row)
                if fill is None:
                    continue
                risk_decision = self._evaluate_pre_trade(fill, row, position_size_pct)
                risk_decisions.append(risk_decision)
                if not risk_decision.approved:
                    self._risk_signals.append({
                        "date": date,
                        "action": "RISK_REJECT",
                        "symbol": fill.signal.symbol,
                        "reason": risk_decision.reason,
                        "policy": next(
                            (item.policy_id for item in risk_decision.decisions if not item.approved),
                            "unknown",
                        ),
                    })
                    continue
                record = self._apply_next_bar_fill(fill, position_size_pct)
                if record is not None:
                    filled_actions.append(fill.signal.action)
                try:
                    audit.log_decision(
                        action=fill.signal.action,
                        symbol=fill.signal.symbol,
                        price=fill.price,
                        quantity=record["quantity"] if record else 0,
                        strategy=strategy.__class__.__name__,
                        reason=fill.signal.reason,
                        portfolio_value=self.portfolio.total_value,
                    )
                except Exception:
                    pass

            signal = strategy.on_bar(i, bar.history, self.portfolio)
            if isinstance(signal, Signal):
                if self._market_rejects(signal, bar.history, i):
                    signals_log.append({
                        "date": date,
                        "action": "SKIP",
                        "symbol": signal.symbol,
                        "price": signal.price,
                        "reason": "多因子择时过滤",
                    })
                else:
                    scheduled = event_loop.schedule(signal, i)
                    signals_log.append({
                        "date": date,
                        "action": signal.action,
                        "symbol": signal.symbol,
                        "price": signal.price,
                        "reason": signal.reason,
                        "available_at": bar.available_at.isoformat(),
                        "earliest_execution_at": scheduled.eligible_at.isoformat() if scheduled else None,
                    })
            elif signal is not None:
                signals_log.append(signal)

            held_symbols = {key.removeprefix("SHORT_") for key in self.portfolio.positions}
            if resolved_symbol:
                held_symbols.add(resolved_symbol)
            prices = {held_symbol: float(row["close"]) for held_symbol in held_symbols}
            self.portfolio.mark_to_market(date, prices)
            if self.risk:
                self.risk.update_equity(self.portfolio.total_value)
                if "BUY" in filled_actions and self.risk.circuit_triggered:
                    self._risk_signals.append({
                        "date": date,
                        "action": "RISK_SKIP",
                        "reason": f"熔断: {self.risk.circuit_reason}",
                    })

        self._fill_stats = dict(fill_model.stats)
        result = {
            "portfolio": self.portfolio,
            "signals": signals_log,
            "metrics": self._calc_metrics(),
            "execution_semantics": "next_bar_open",
            "random_seed": self.random_seed,
            "risk_decisions": risk_decisions,
        }
        if self.risk:
            result["risk_report"] = self.risk.report()
            result["risk_logs"] = self.risk.get_recent_logs(20)
            result["risk_signals"] = self._risk_signals
        return result

    def _apply_next_bar_fill(self, fill, position_size_pct: float):
        signal = fill.signal
        price = float(fill.price)
        date = fill.executed_at.date().isoformat()
        if signal.action == "BUY":
            short_key = "SHORT_" + signal.symbol
            if short_key in self.portfolio.positions:
                qty = self.portfolio.positions[short_key]["qty"]
                self.portfolio.cover_short(signal.symbol, price, qty, date, self.commission_rate)
            max_cost = self.portfolio.total_value * position_size_pct
            qty = signal.quantity if signal.quantity > 0 else int(max_cost / price / 100) * 100
            return self.portfolio.buy(signal.symbol, price, qty, date, self.commission_rate) if qty > 0 else None
        if signal.action == "SELL" and signal.symbol in self.portfolio.positions:
            qty = signal.quantity if signal.quantity > 0 else self.portfolio.positions[signal.symbol]["qty"]
            return self.portfolio.sell(signal.symbol, price, qty, date, self.commission_rate)
        if signal.action == "SHORT":
            if signal.symbol in self.portfolio.positions:
                qty = self.portfolio.positions[signal.symbol]["qty"]
                self.portfolio.sell(signal.symbol, price, qty, date, self.commission_rate)
            max_cost = self.portfolio.total_value * position_size_pct
            qty = signal.quantity if signal.quantity > 0 else int(max_cost / price / 100) * 100
            return self.portfolio.short(signal.symbol, price, qty, date, self.commission_rate) if qty > 0 else None
        if signal.action == "COVER":
            short_key = "SHORT_" + signal.symbol
            if short_key in self.portfolio.positions:
                qty = signal.quantity if signal.quantity > 0 else self.portfolio.positions[short_key]["qty"]
                return self.portfolio.cover_short(signal.symbol, price, qty, date, self.commission_rate)
        return None

    def _evaluate_pre_trade(self, fill, row, position_size_pct: float):
        from src.lxl_quantaxis.risk.policies import LegacyRiskPolicy
        from src.lxl_quantaxis.risk.pre_trade import OrderIntent, PortfolioRiskSnapshot, RiskPolicyChain

        signal = fill.signal
        price = float(fill.price)
        max_cost = self.portfolio.total_value * position_size_pct
        quantity = signal.quantity if signal.quantity > 0 else int(max_cost / price / 100) * 100
        positions = {
            key.removeprefix("SHORT_"): value["qty"] * value.get("last_price", value["avg_cost"])
            for key, value in self.portfolio.positions.items()
        }
        peak = float(getattr(self.risk, "peak_equity", self.portfolio.total_value))
        chain = self.risk_policy_chain
        if chain is None:
            policies = (LegacyRiskPolicy(self.risk),) if self.risk is not None else ()
            chain = RiskPolicyChain(policies)
        order = OrderIntent(
            order_id=f"bt-{fill.signal_available_at.isoformat()}-{signal.symbol}-{signal.action}",
            action=signal.action,
            symbol=signal.symbol,
            quantity=quantity,
            price=price,
            average_daily_volume=float(row.get("volume", 0.0)),
        )
        snapshot = PortfolioRiskSnapshot(
            equity=self.portfolio.total_value,
            cash=self.portfolio.cash,
            peak_equity=peak,
            position_values=positions,
            sector_values={},
            kill_switch=False,
        )
        return chain.evaluate(order, snapshot)

    def _market_rejects(self, signal: Signal, history: pd.DataFrame, index: int) -> bool:
        if not self.use_market_filter or signal.action != "BUY" or index < 60:
            return False
        try:
            from src.factors.definitions import FactorCalculator

            factors = FactorCalculator(history).compute_all().iloc[-1]
            score = (
                float(factors.get("ma_slope", 0.5))
                + float(factors.get("ma_alignment", 0.5))
                + float(factors.get("price_position", 0.5))
            ) / 3
            return score < 0.4
        except Exception:
            return False

    @staticmethod
    def slippage_sensitivity(strategy, data: "pd.DataFrame",
                             slippages: list = None,
                             **kwargs) -> "pd.DataFrame":
        """
        滑点敏感度分析

        参数:
          strategy: 策略对象
          data:     OHLCV 数据
          slippages: 滑点列表, 默认 [0, 0.001, 0.003, 0.005, 0.01]

        返回:
          DataFrame: slippage | 年化收益 | 夏普 | 最大回撤 | 交易次数
        """
        import pandas as pd

        if slippages is None:
            slippages = [0, 0.001, 0.003, 0.005, 0.01]

        rows = []
        for sl in slippages:
            engine = BacktestEngine(slippage=sl, **kwargs)
            result = engine.run(strategy, data.copy())
            m = result["metrics"]
            try:
                ret = float(str(m.get("总收益率", "0")).replace("%", "").replace("+", ""))
            except:
                ret = 0
            try:
                sharpe = float(str(m.get("夏普比率", 0)))
            except:
                sharpe = 0
            try:
                dd = float(str(m.get("最大回撤", "0")).replace("%", "").replace("-", ""))
            except:
                dd = 0
            rows.append({
                "滑点": f"{sl*100:.1f}%",
                "年化收益": round(ret, 2),
                "夏普比率": round(sharpe, 2),
                "最大回撤": round(dd, 2),
                "交易次数": len(result["portfolio"].trade_log),
            })

        return pd.DataFrame(rows)

    def _calc_metrics(self) -> dict:
        """从 portfolio.daily_values 计算绩效指标"""
        from src.backtest.metrics import calc_all_metrics
        return calc_all_metrics(
            self.portfolio.daily_values,
            self.portfolio.trade_log,
            self.initial_capital,
        )

    @property
    def fill_stats(self) -> dict:
        """限价单成交统计"""
        a = self._fill_stats["attempted"]
        if a == 0:
            return {"fill_rate": 1.0, "attempted": 0, "filled": 0}
        return {
            "fill_rate": round(self._fill_stats["filled"] / a * 100, 1),
            **self._fill_stats,
        }
