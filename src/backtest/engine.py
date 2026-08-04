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

    def __init__(self, initial_capital: float = 100_000,
                 commission_rate: float = 0.0003,
                 stamp_duty_rate: float = 0.0005,
                 transfer_fee_rate: float = 0.0001,
                 min_commission: float = 5.0):
        """
        A股真实交易成本模型

        参数:
            commission_rate:  佣金费率 (默认 0.03%, 双向)
            stamp_duty_rate:  印花税率 (0.05%, 仅卖出方)
            transfer_fee_rate: 过户费率 (0.001%, 仅沪市, 双向)
            min_commission:    最低佣金 (5元/笔, 不足5元按5元计)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, dict] = {}     # symbol -> {qty, avg_cost}
        self.trade_log: List[dict] = []           # 交易记录
        self.daily_values: List[dict] = []        # 每日净值
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.min_commission = min_commission

    @staticmethod
    def _is_shanghai(symbol: str) -> bool:
        """判断是否沪市股票 (需收过户费): 6开头(主板/科创板) 或 588开头(科创板ETF)"""
        s = str(symbol).strip()
        return s.startswith("6") or s.startswith("588") or s.startswith("51")

    def _calc_buy_cost(self, price: float, quantity: int) -> dict:
        """计算买入成本明细"""
        amount = price * quantity
        # 佣金 (最低5元)
        commission = max(amount * self.commission_rate, self.min_commission)
        # 过户费 (仅沪市)
        transfer_fee = amount * self.transfer_fee_rate if self._is_shanghai(
            str(getattr(self, "_current_symbol", ""))) else 0
        total_fee = commission + transfer_fee
        return {
            "amount": round(amount, 2),
            "commission": round(commission, 2),
            "stamp_duty": 0.0,
            "transfer_fee": round(transfer_fee, 2),
            "total_fee": round(total_fee, 2),
            "total_cost": round(amount + total_fee, 2),
        }

    def _calc_sell_cost(self, price: float, quantity: int) -> dict:
        """计算卖出成本明细"""
        amount = price * quantity
        # 佣金 (最低5元)
        commission = max(amount * self.commission_rate, self.min_commission)
        # 印花税 (仅卖出方, 0.05%)
        stamp_duty = amount * self.stamp_duty_rate
        # 过户费 (仅沪市)
        transfer_fee = amount * self.transfer_fee_rate if self._is_shanghai(
            str(getattr(self, "_current_symbol", ""))) else 0
        total_fee = commission + stamp_duty + transfer_fee
        return {
            "amount": round(amount, 2),
            "commission": round(commission, 2),
            "stamp_duty": round(stamp_duty, 2),
            "transfer_fee": round(transfer_fee, 2),
            "total_fee": round(total_fee, 2),
            "net_proceeds": round(amount - total_fee, 2),
        }

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
            date: str, commission_rate: float = None):
        """买入 (含佣金+过户费, 最低佣金5元)"""
        self._current_symbol = symbol
        cr = commission_rate if commission_rate is not None else self.commission_rate

        cost = price * quantity
        # 用真实成本模型估算
        est_commission = max(cost * cr, self.min_commission)
        est_transfer = cost * self.transfer_fee_rate if self._is_shanghai(symbol) else 0
        est_total = cost + est_commission + est_transfer

        if est_total > self.cash:
            # 资金不足，按可买数量调整 (保守用费率估算)
            affordable_qty = int(self.cash / (price * (1 + cr + self.transfer_fee_rate)))
            # 降到整手
            affordable_qty = (affordable_qty // 100) * 100
            if affordable_qty <= 0:
                return None
            quantity = affordable_qty
            cost = price * quantity

        # 精确计算成本
        fee_detail = self._calc_buy_cost(price, quantity)
        commission = fee_detail["commission"]
        transfer_fee = fee_detail["transfer_fee"]
        total_cost = fee_detail["total_cost"]

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
            "price": price, "quantity": quantity,
            "commission": round(commission, 2),
            "stamp_duty": 0.0,
            "transfer_fee": round(transfer_fee, 2),
            "total_fee": round(commission + transfer_fee, 2),
            "fee": round(commission + transfer_fee, 2),  # 向后兼容
            "cost": round(cost, 2), "cash_after": round(self.cash, 2),
        }
        self.trade_log.append(record)
        return record

    def sell(self, symbol: str, price: float, quantity: int,
             date: str, commission_rate: float = None):
        """卖出 (含佣金+印花税+过户费, 最低佣金5元)"""
        self._current_symbol = symbol
        cr = commission_rate if commission_rate is not None else self.commission_rate

        if symbol not in self.positions or self.positions[symbol]["qty"] <= 0:
            return None

        qty = min(quantity, self.positions[symbol]["qty"])
        proceeds = price * qty

        # 精确计算成本
        fee_detail = self._calc_sell_cost(price, qty)
        commission = fee_detail["commission"]
        stamp_duty = fee_detail["stamp_duty"]
        transfer_fee = fee_detail["transfer_fee"]
        net_proceeds = fee_detail["net_proceeds"]

        # 计算盈亏
        avg_cost = self.positions[symbol]["avg_cost"]
        pnl = (price - avg_cost) * qty - (commission + stamp_duty + transfer_fee)

        self.cash += net_proceeds
        self.positions[symbol]["qty"] -= qty
        self.positions[symbol]["last_price"] = price

        if self.positions[symbol]["qty"] <= 0:
            del self.positions[symbol]

        record = {
            "date": date, "symbol": symbol, "action": "SELL",
            "price": price, "quantity": qty,
            "commission": round(commission, 2),
            "stamp_duty": round(stamp_duty, 2),
            "transfer_fee": round(transfer_fee, 2),
            "total_fee": round(commission + stamp_duty + transfer_fee, 2),
            "fee": round(commission + stamp_duty + transfer_fee, 2),  # 向后兼容
            "proceeds": round(net_proceeds, 2), "pnl": round(pnl, 2),
            "cash_after": round(self.cash, 2),
        }
        self.trade_log.append(record)
        return record

    def short(self, symbol: str, price: float, quantity: int,
             date: str, commission_rate: float = None):
        """做空 (含佣金+过户费)"""
        self._current_symbol = symbol
        cr = commission_rate if commission_rate is not None else self.commission_rate

        cost = price * quantity
        est_commission = max(cost * cr, self.min_commission)
        est_transfer = cost * self.transfer_fee_rate if self._is_shanghai(symbol) else 0

        if cost + est_commission + est_transfer > self.cash:
            affordable = int(self.cash / (price * (1 + cr + self.transfer_fee_rate)))
            affordable = (affordable // 100) * 100
            if affordable <= 0: return None
            quantity = affordable
            cost = price * quantity

        fee_detail = self._calc_buy_cost(price, quantity)
        commission = fee_detail["commission"]
        transfer_fee = fee_detail["transfer_fee"]

        self.cash -= (commission + transfer_fee)  # 只扣手续费，做空获得现金
        self.cash += cost  # 卖出获得现金

        short_key = "SHORT_" + symbol
        self.positions[short_key] = {"qty": quantity, "avg_cost": price, "last_price": price}

        record = {"date": date, "symbol": symbol, "action": "SHORT",
                  "price": price, "quantity": quantity,
                  "commission": round(commission, 2),
                  "transfer_fee": round(transfer_fee, 2),
                  "total_fee": round(commission + transfer_fee, 2),
                  "fee": round(commission + transfer_fee, 2),  # 向后兼容
                  "cash_after": round(self.cash, 2)}
        self.trade_log.append(record)
        return record

    def cover_short(self, symbol: str, price: float, quantity: int,
                   date: str, commission_rate: float = None):
        """平空 (含佣金+印花税+过户费)"""
        self._current_symbol = symbol
        cr = commission_rate if commission_rate is not None else self.commission_rate

        short_key = "SHORT_" + symbol
        if short_key not in self.positions: return None

        qty = min(quantity, self.positions[short_key]["qty"])
        cost = price * qty

        fee_detail = self._calc_sell_cost(price, qty)
        commission = fee_detail["commission"]
        stamp_duty = fee_detail["stamp_duty"]
        transfer_fee = fee_detail["transfer_fee"]
        total_fee = commission + stamp_duty + transfer_fee

        if cost + total_fee > self.cash:
            qty = int(self.cash / (price * (1 + cr + self.stamp_duty_rate + self.transfer_fee_rate)))
            qty = (qty // 100) * 100
            if qty <= 0: return None
            cost = price * qty
            fee_detail = self._calc_sell_cost(price, qty)
            commission = fee_detail["commission"]
            stamp_duty = fee_detail["stamp_duty"]
            transfer_fee = fee_detail["transfer_fee"]
            total_fee = commission + stamp_duty + transfer_fee

        self.cash -= (cost + total_fee)

        entry_price = self.positions[short_key]["avg_cost"]
        pnl = (entry_price - price) * qty - total_fee  # 做空: 跌了赚钱

        self.positions[short_key]["qty"] -= qty
        if self.positions[short_key]["qty"] <= 0:
            del self.positions[short_key]

        record = {"date": date, "symbol": symbol, "action": "COVER",
                  "price": price, "quantity": qty,
                  "commission": round(commission, 2),
                  "stamp_duty": round(stamp_duty, 2),
                  "transfer_fee": round(transfer_fee, 2),
                  "total_fee": round(total_fee, 2),
                  "fee": round(total_fee, 2),  # 向后兼容
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
                 use_market_filter: bool = False,
                 use_risk_manager: bool = True,
                 # A股真实交易成本
                 stamp_duty_rate: float = 0.0005,
                 transfer_fee_rate: float = 0.0001,
                 min_commission: float = 5.0,
                 # 无风险利率 (可用国债收益率替代, 默认2%)
                 risk_free_rate: float = 0.02,
                 # 微观结构 (v6.6)
                 use_impact_cost: bool = True,
                 use_limit_order: bool = False,
                 impact_coefficient: float = 0.1,
                 token_validator=None):  # 陷阱4: Token过期检查回调
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.min_commission = min_commission
        self.risk_free_rate = risk_free_rate
        self.use_market_filter = use_market_filter
        self.use_risk_manager = use_risk_manager
        self.use_impact_cost = use_impact_cost
        self.use_limit_order = use_limit_order
        self.impact_coefficient = impact_coefficient
        self.portfolio = Portfolio(
            initial_capital,
            commission_rate=commission_rate,
            stamp_duty_rate=stamp_duty_rate,
            transfer_fee_rate=transfer_fee_rate,
            min_commission=min_commission,
        )
        # 风控管理器
        self.risk = None
        if use_risk_manager:
            from src.risk.manager import RiskManager
            self.risk = RiskManager(initial_capital=initial_capital)
        self.token_validator = token_validator  # 陷阱4
        self._risk_signals = []  # 风控产生的信号记录
        self._fill_stats = {"attempted": 0, "filled": 0, "cancelled": 0}

    def run(self, strategy, data: pd.DataFrame,
            position_size_pct: float = 0.2,
            execution_mode: str = "next_open",
            benchmark_data: "pd.DataFrame" = None) -> dict:
        """
        执行回测

        参数:
            strategy: 策略对象（需实现 on_bar 方法）
            data: OHLCV DataFrame（需包含 date, open, high, low, close, volume 列）
            position_size_pct: 单笔仓位占比
            execution_mode: 成交模式
                "next_open" (默认): 信号T日收盘后生成, T+1日开盘价成交 (无前视偏差)
                "same_close":       信号T日收盘后生成, T日收盘价成交 (有前视偏差, 仅用于对比)
            benchmark_data: 基准OHLCV数据 (如沪深300), 传入后计算 Alpha/Beta/IR

        返回:
            dict: {
                "portfolio": Portfolio 对象,
                "signals": 产生的信号列表,
                "metrics": 绩效指标字典,
            }
        """
        # 准备基准净值序列
        bench_values = None
        if benchmark_data is not None and len(benchmark_data) >= 2:
            bd = benchmark_data.sort_values("date").reset_index(drop=True)
            bench_values = [
                {"date": str(r["date"])[:10], "total_value": r["close"]}
                for _, r in bd.iterrows()
            ]

        if execution_mode == "same_close":
            return self._run_legacy(strategy, data, position_size_pct, bench_values)
        return self._run_next_bar(strategy, data, position_size_pct, bench_values)

    # ═════════════════════════════════════════════════════════
    # 旧模式: 同日收盘价成交 (有前视偏差, 仅用于对比)
    # ═════════════════════════════════════════════════════════
    def _run_legacy(self, strategy, data: pd.DataFrame,
                    position_size_pct: float = 0.2,
                    bench_values: list = None) -> dict:
        # 审计日志
        from src.audit.TradeAudit import audit

        self.portfolio = Portfolio(
            self.initial_capital,
            commission_rate=self.commission_rate,
            stamp_duty_rate=self.stamp_duty_rate,
            transfer_fee_rate=self.transfer_fee_rate,
            min_commission=self.min_commission,
        )
        signals_log = []

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
        metrics = self._calc_metrics(bench_values)

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

    # ═════════════════════════════════════════════════════════
    # 新模式: 下一根K线开盘价成交 (无前视偏差, 默认)
    # 信号T日收盘后生成 → T+1日开盘价成交
    # ═════════════════════════════════════════════════════════
    def _run_next_bar(self, strategy, data: pd.DataFrame,
                      position_size_pct: float = 0.2,
                      bench_values: list = None) -> dict:
        """
        无前视偏差的回测引擎

        流程 (每个 bar i):
          1. 如果有上一根 bar 产生的待执行信号 → 以今日 OPEN 价成交
          2. 用 data.iloc[:i+1] 调用策略 on_bar 生成信号 (看到今日收盘)
          3. 将信号暂存为 pending (明日执行)
          4. 按今日 CLOSE 价 mark-to-market
        """
        from src.audit.TradeAudit import audit

        self.portfolio = Portfolio(
            self.initial_capital,
            commission_rate=self.commission_rate,
            stamp_duty_rate=self.stamp_duty_rate,
            transfer_fee_rate=self.transfer_fee_rate,
            min_commission=self.min_commission,
        )
        signals_log = []
        pending_signal = None       # 上一根 bar 产生的待执行信号
        pending_date = None         # 信号产生的日期
        import random as _rng

        data = data.sort_values("date").reset_index(drop=True)

        for i in range(len(data)):
            # 陷阱4: 每100根bar检查一次token是否过期
            if self.token_validator and i % 100 == 0:
                try:
                    self.token_validator()
                except Exception:
                    raise

            row = data.iloc[i]
            date = str(row["date"])[:10]

            # ── 1. 执行上一根bar的待执行信号, 以今日 OPEN 价成交 ──
            if pending_signal is not None:
                exec_price = row["open"]

                # 1a. 涨跌停检查 (A股: 涨停不能买, 跌停不能卖)
                pct_change = 0.0
                if i > 0:
                    prev_close = data.iloc[i - 1]["close"]
                    if prev_close > 0:
                        pct_change = (row["open"] - prev_close) / prev_close

                # 涨停 ≈ +10% (ST股 +5%, 创业板/科创板 +20%), 保守用 +9.5% 判定
                is_limit_up = pct_change >= 0.095
                # 跌停 ≈ -10%
                is_limit_down = pct_change <= -0.095

                if (pending_signal.action == "BUY" and is_limit_up) or \
                   (pending_signal.action in ("SELL", "COVER") and is_limit_down):
                    signals_log.append({
                        "date": date, "action": "LIMIT_BLOCKED",
                        "symbol": pending_signal.symbol,
                        "price": round(exec_price, 2),
                        "reason": f"涨跌停限制, 无法成交 (变动{pct_change*100:+.1f}%)",
                    })
                    pending_signal = None
                    pending_date = None
                else:
                    # 1b. 微观结构模拟 (v6.6) — 基于执行 bar 的数据
                    impact_cost = 0.0
                    if self.use_impact_cost and pending_signal.action in ("BUY", "SELL"):
                        daily_vol = row.get("volume", 1)
                        if daily_vol > 0:
                            order_ratio = (exec_price * max(pending_signal.quantity, 1)) / (exec_price * daily_vol)
                            if order_ratio > 0.01:
                                impact_cost = self.impact_coefficient * order_ratio

                    # 1c. 限价单模拟
                    fill_price = exec_price
                    filled = True
                    if self.use_limit_order and pending_signal.action == "BUY":
                        self._fill_stats["attempted"] += 1
                        queue_pos = _rng.randint(0, 100)
                        if queue_pos < 70:
                            spread = exec_price * _rng.uniform(0.0001, 0.001)
                            fill_price = exec_price - spread
                            self._fill_stats["filled"] += 1
                        else:
                            filled = False
                            self._fill_stats["cancelled"] += 1

                    if filled:
                        # 最终执行价 = 开盘价 + 滑点 + 冲击成本
                        if pending_signal.action == "BUY":
                            final_price = fill_price * (1 + self.slippage + impact_cost)
                        else:
                            final_price = fill_price * (1 - self.slippage - impact_cost)

                        # 执行信号
                        if pending_signal.action == "BUY":
                            # 先平空头(如有)
                            short_key = "SHORT_" + pending_signal.symbol
                            if short_key in self.portfolio.positions:
                                qty = self.portfolio.positions[short_key]["qty"]
                                self.portfolio.cover_short(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)
                            # 开多头
                            max_cost = self.portfolio.total_value * position_size_pct
                            qty = pending_signal.quantity if pending_signal.quantity > 0 else \
                                int(max_cost / final_price / 100) * 100
                            if qty > 0:
                                self.portfolio.buy(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)
                                # 风控: 记录新持仓
                                if self.risk:
                                    self.risk.add_position(pending_signal.symbol, final_price)

                        elif pending_signal.action == "SELL":
                            if pending_signal.symbol in self.portfolio.positions:
                                qty = pending_signal.quantity if pending_signal.quantity > 0 else \
                                    self.portfolio.positions[pending_signal.symbol]["qty"]
                                self.portfolio.sell(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)
                                if self.risk:
                                    self.risk.remove_position(pending_signal.symbol)

                        elif pending_signal.action == "SHORT":
                            if pending_signal.symbol in self.portfolio.positions:
                                qty = self.portfolio.positions[pending_signal.symbol]["qty"]
                                self.portfolio.sell(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)
                            max_cost = self.portfolio.total_value * position_size_pct
                            qty = pending_signal.quantity if pending_signal.quantity > 0 else \
                                int(max_cost / final_price / 100) * 100
                            if qty > 0:
                                self.portfolio.short(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)

                        elif pending_signal.action == "COVER":
                            short_key = "SHORT_" + pending_signal.symbol
                            if short_key in self.portfolio.positions:
                                qty = pending_signal.quantity if pending_signal.quantity > 0 else \
                                    self.portfolio.positions[short_key]["qty"]
                                self.portfolio.cover_short(
                                    pending_signal.symbol, final_price, qty, date, self.commission_rate)

                        # 审计记录
                        try:
                            qty = pending_signal.quantity if pending_signal.quantity > 0 else 0
                            audit.log_decision(
                                action=pending_signal.action, symbol=pending_signal.symbol,
                                price=final_price, quantity=qty,
                                strategy=strategy.__class__.__name__,
                                reason=pending_signal.reason,
                                portfolio_value=self.portfolio.total_value,
                            )
                        except:
                            pass

                        # 风控: 更新权益
                        if self.risk:
                            self.risk.update_equity(self.portfolio.total_value)
                            if pending_signal.action == "BUY" and self.risk.circuit_triggered:
                                self._risk_signals.append({
                                    "date": date, "action": "RISK_SKIP",
                                    "reason": f"熔断: {self.risk.circuit_reason}"
                                })

                    pending_signal = None
                    pending_date = None

            # ── 2. 生成信号 (基于到今日为止的数据, 含今日收盘) ──
            bar_data = data.iloc[:i + 1].copy()
            signal = strategy.on_bar(i, bar_data, self.portfolio)

            if signal is None:
                prices = {row.get("symbol", ""): row["close"]}
                self.portfolio.mark_to_market(date, prices)
                continue

            if not isinstance(signal, Signal):
                signals_log.append(signal)
                prices = {row.get("symbol", ""): row["close"]}
                self.portfolio.mark_to_market(date, prices)
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
                        pass

            # 记录信号 (明日执行)
            signals_log.append({
                "date": date, "action": signal.action,
                "symbol": signal.symbol, "price": signal.price,
                "reason": signal.reason,
            })
            pending_signal = signal
            pending_date = date

            # ── 3. 按收盘价估值 ──
            prices = {row.get("symbol", ""): row["close"]}
            self.portfolio.mark_to_market(date, prices)

            # ── 4. 风控: 检查移动止损 ──
            if self.risk and self.risk.positions:
                symbol = row.get("symbol", "")
                if symbol in self.risk.positions:
                    should_stop, stop_reason = self.risk.check(symbol, row["close"])
                    if should_stop:
                        # 生成止损信号 (下一根 bar 执行)
                        stop_signal = Signal(
                            symbol=symbol,
                            action="SELL",
                            date=date,
                            price=row["close"],
                            quantity=0,
                            reason=stop_reason,
                        )
                        signals_log.append({
                            "date": date, "action": "RISK_SELL",
                            "symbol": symbol, "price": row["close"],
                            "reason": stop_reason,
                        })
                        pending_signal = stop_signal

        # 最后一根 bar 的 pending 信号无法在下一日成交
        if pending_signal is not None:
            signals_log.append({
                "date": pending_date or date, "action": "UNFILLED",
                "symbol": pending_signal.symbol, "price": pending_signal.price,
                "reason": "最后信号无下一日开盘价可成交",
            })

        # 计算绩效指标
        metrics = self._calc_metrics(bench_values)

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

    def _calc_metrics(self, benchmark_values=None) -> dict:
        """从 portfolio.daily_values 计算绩效指标"""
        from src.backtest.metrics import calc_all_metrics
        return calc_all_metrics(
            self.portfolio.daily_values,
            self.portfolio.trade_log,
            self.initial_capital,
            risk_free_rate=getattr(self, 'risk_free_rate', 0.02),
            benchmark_values=benchmark_values,
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
