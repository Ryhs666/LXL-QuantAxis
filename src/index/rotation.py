"""
指数策略 — 轮动 + 定投

核心功能:
  - 动量轮动: 每周期买入近期表现最强的 N 个指数
  - 估值轮动: 超配低估指数，低配高估指数
  - 定投回测: 模拟定期定额/不定额投资
  - 增强定投: 估值越低买越多
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict

from src.backtest.data_feed import get_data, get_index_data
from src.index.valuation import INDEX_ETF_MAP, FAVORITE_INDICES
from src.config import config


# ============================================================
# 1. 动量轮动策略
# ============================================================

class IndexRotation:
    """
    指数动量轮动

    逻辑:
      - 每 N 个交易日检查一次
      - 计算所有候选指数过去 M 日的涨幅
      - 买入涨幅最强的 Top-K 个
      - 已持有的掉出 Top-K 则卖出

    参数:
        lookback_days: 动量计算周期 (默认 20 个交易日)
        top_k: 持有前 K 个最强指数 (默认 2)
        rebalance_freq: 调仓频率，每 N 个交易日 (默认 5)
        use_etf: True=用ETF回测, False=用指数价格回测
    """

    def __init__(self, indices: list = None,
                 lookback_days: int = 20, top_k: int = 2,
                 rebalance_freq: int = 5, use_etf: bool = True):
        self.indices = indices or FAVORITE_INDICES[:4]
        self.lookback_days = lookback_days
        self.top_k = top_k
        self.rebalance_freq = rebalance_freq
        self.use_etf = use_etf

    def run(self, start_date: str = "2020-01-01",
            end_date: str = None, initial_capital: float = None) -> dict:
        """
        运行指数轮动回测
        """
        if initial_capital is None:
            initial_capital = config.initial_capital

        # 加载所有指数数据(直接用指数代码，不用ETF)
        print(f"\n  加载 {len(self.indices)} 个指数数据...")
        index_data = {}
        for code in self.indices:
            name, etf, _, market = INDEX_ETF_MAP.get(code, (code, "N/A", "", "指数"))
            try:
                # 指数代码直接用 get_index_data
                df = get_index_data(code, start_date=start_date, end_date=end_date)
                if df is not None and len(df) > 50:
                    df["date"] = pd.to_datetime(df["date"])
                    index_data[code] = df
                    print(f"    {name} ({code}): {len(df)} 条")
            except Exception as e:
                print(f"    ⚠️ {name} ({code}): {e}")

        if len(index_data) < 2:
            print("  ❌ 数据不足，至少需要2个指数")
            return {}

        # 对齐日期
        all_dates = set()
        for df in index_data.values():
            all_dates.update(df["date"].tolist())
        all_dates = sorted(all_dates)

        # 模拟交易
        cash = initial_capital
        holdings: Dict[str, dict] = {}  # code -> {shares, cost}
        trade_log = []
        daily_values = []

        for i, date in enumerate(all_dates):
            # 调仓日
            if i % self.rebalance_freq == 0 and i >= self.lookback_days:
                # 计算每个指数的动量
                momentum = {}
                for code, df in index_data.items():
                    df_before = df[df["date"] <= date]
                    if len(df_before) < self.lookback_days:
                        continue
                    ret = (df_before["close"].iloc[-1] /
                           df_before["close"].iloc[-self.lookback_days] - 1) * 100
                    momentum[code] = ret

                # 排名
                ranked = sorted(momentum.items(), key=lambda x: x[1], reverse=True)
                top_set = set(code for code, _ in ranked[:self.top_k])

                # 卖出掉出排名的
                for code in list(holdings.keys()):
                    if code not in top_set:
                        price_now = self._get_price(index_data, code, date)
                        if price_now is None:
                            continue
                        shares = holdings[code]["shares"]
                        cash += shares * price_now * 0.999  # 千分之一手续费
                        trade_log.append({
                            "date": str(date)[:10], "code": code,
                            "action": "SELL", "price": price_now,
                            "shares": shares, "cash": round(cash, 2),
                            "reason": "动量排名下降",
                        })
                        del holdings[code]

                # 买入新入选的（指数按份数交易，支持小数份额）
                if len(holdings) < self.top_k and top_set:
                    per_slot = cash / (self.top_k - len(holdings) + 1)
                    for code in top_set:
                        if code in holdings:
                            continue
                        price_now = self._get_price(index_data, code, date)
                        if price_now is None or price_now <= 0:
                            continue
                        # 指数交易用份数（小数），不用手数
                        shares = int(per_slot / price_now)
                        if shares > 0:
                            cost = shares * price_now * 1.001
                            if cost <= cash:
                                cash -= cost
                                holdings[code] = {"shares": shares, "cost": price_now}
                                trade_log.append({
                                    "date": str(date)[:10], "code": code,
                                    "action": "BUY", "price": price_now,
                                    "shares": shares, "cash": round(cash, 2),
                                    "reason": f"动量排名 Top{self.top_k}: {momentum.get(code,0):+.1f}%",
                                })

            # 每日估值
            position_value = 0
            for code, h in holdings.items():
                price_now = self._get_price(index_data, code, date)
                if price_now:
                    position_value += h["shares"] * price_now

            daily_values.append({
                "date": str(date)[:10],
                "cash": round(cash, 2),
                "position_value": round(position_value, 2),
                "total_value": round(cash + position_value, 2),
                "holdings_count": len(holdings),
            })

        # 计算指标
        total_values = [d["total_value"] for d in daily_values]
        final_value = total_values[-1] if total_values else initial_capital
        total_return = (final_value / initial_capital - 1) * 100

        # 年化
        days = len(daily_values)
        years = max(days / 252, 0.01)
        annual_return = ((final_value / initial_capital) ** (1 / years) - 1) * 100

        # 最大回撤
        peak = total_values[0]
        max_dd = 0
        for v in total_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # 胜率
        sells = [t for t in trade_log if t["action"] == "SELL"]
        wins_list = []
        for s in sells:
            buy = next((t for t in trade_log if t["action"] == "BUY" and t["code"] == s["code"]), None)
            if buy:
                wins_list.append(s["price"] > buy["price"])

        win_rate = sum(wins_list) / len(wins_list) * 100 if wins_list else 0

        metrics = {
            "策略": f"指数轮动 (Top{self.top_k}, {self.lookback_days}日动量)",
            "初始资金": f"¥{initial_capital:,.0f}",
            "最终权益": f"¥{final_value:,.0f}",
            "总收益率": f"{total_return:+.2f}%",
            "年化收益率": f"{annual_return:+.2f}%",
            "最大回撤": f"{max_dd:.2f}%",
            "交易次数": len(trade_log),
            "胜率": f"{win_rate:.1f}%",
            "候选指数": ", ".join(self.indices),
        }

        return {
            "metrics": metrics,
            "trade_log": trade_log,
            "daily_values": daily_values,
            "index_data": index_data,
        }

    def _get_price(self, index_data: dict, code: str, date) -> Optional[float]:
        if code not in index_data:
            return None
        df = index_data[code]
        match = df[df["date"] <= date]
        if match.empty:
            return None
        return match["close"].iloc[-1]


# ============================================================
# 2. 定投回测引擎
# ============================================================

class DCABacktest:
    """
    定投回测

    支持:
      - 定期定额 (每月固定金额)
      - 定期不定额 (估值越低买越多)
      - 多种定投频率 (每周/每两周/每月)
    """

    def __init__(self, symbol: str, market: str = "指数"):
        self.symbol = symbol
        self.market = market

    def run(self,
            amount_per_period: float = 5000,
            frequency: str = "monthly",   # "weekly" | "biweekly" | "monthly"
            start_date: str = "2018-01-01",
            end_date: str = None,
            enhanced: bool = False,       # True=估值增强(越跌越买)
            base_pe: float = 15,          # 基准PE，低于此值加倍买
            verbose: bool = True) -> dict:
        """
        运行定投回测

        enhanced=True 时:
          PE < base_pe*0.7 → 2倍买入
          PE < base_pe*0.5 → 3倍买入
          PE > base_pe*1.5 → 0.5倍买入(减半)
          PE > base_pe*2.0 → 暂停买入
        """
        name = INDEX_ETF_MAP.get(self.symbol, (self.symbol, "", "", ""))[0]
        if verbose:
            print(f"\n  定投回测: {name} ({self.symbol})")
            print(f"    每期 ¥{amount_per_period:,.0f} | 频率: {frequency} | "
                  f"{'增强模式' if enhanced else '普通模式'}")

        # 获取数据
        try:
            # 先试指数代码
            data = get_index_data(self.symbol, start_date=start_date, end_date=end_date)
            if data is None or len(data) < 20:
                raise ValueError("指数数据不足")
        except Exception:
            # 回退到ETF/股票代码
            data = get_data(self.symbol, self.market, start_date=start_date, end_date=end_date)
        data["date"] = pd.to_datetime(data["date"])

        if verbose:
            print(f"    数据: {len(data)} 条 ({str(data['date'].iloc[0])[:10]} ~ "
                  f"{str(data['date'].iloc[-1])[:10]})")

        # 生成定投日期
        invest_dates = self._gen_dates(data, frequency)

        # 模拟定投
        total_shares = 0
        total_invested = 0
        total_periods = 0
        invest_log = []

        for date in invest_dates:
            match = data[data["date"] <= date]
            if match.empty:
                continue

            price = match["close"].iloc[-1]

            # 计算买入倍数
            multiplier = 1.0
            reason = "普通定投"
            if enhanced:
                multiplier, reason = self._enhanced_multiplier(match)

            invest_amount = amount_per_period * multiplier
            shares = invest_amount / price

            total_shares += shares
            total_invested += invest_amount
            total_periods += 1

            invest_log.append({
                "date": str(date)[:10],
                "price": round(price, 2),
                "amount": round(invest_amount, 2),
                "shares": round(shares, 2),
                "multiplier": multiplier,
                "total_shares": round(total_shares, 2),
                "total_invested": round(total_invested, 2),
                "reason": reason,
            })

        # 计算最终价值
        final_price = data["close"].iloc[-1]
        final_value = total_shares * final_price
        total_return = (final_value / total_invested - 1) * 100 if total_invested > 0 else 0

        # 年化
        years = max((data["date"].iloc[-1] - data["date"].iloc[0]).days / 365, 0.01)
        annual_return = ((final_value / max(total_invested, 1)) ** (1 / years) - 1) * 100

        # IRR 估算
        monthly_irr = self._calc_irr(invest_log, final_price)

        metrics = {
            "标的": f"{name} ({self.symbol})",
            "定投模式": "增强定投" if enhanced else "普通定投",
            "定投期数": total_periods,
            "总投入": f"¥{total_invested:,.0f}",
            "最终市值": f"¥{final_value:,.0f}",
            "总收益率": f"{total_return:+.2f}%",
            "年化收益": f"{annual_return:+.2f}%",
            "年化IRR": f"{monthly_irr:.2f}%",
            "持有份额": f"{total_shares:,.0f}",
            "平均成本": f"¥{total_invested/max(total_shares,1):.2f}",
            "当前价格": f"¥{final_price:.2f}",
        }

        if verbose:
            print(f"\n  📊 定投结果:")
            for k, v in metrics.items():
                print(f"    {k}: {v}")

        return {
            "metrics": metrics,
            "invest_log": invest_log,
            "data": data,
        }

    def _gen_dates(self, data: pd.DataFrame, frequency: str) -> list:
        """生成定投日期"""
        dates = data["date"].tolist()
        if not dates:
            return []

        start = dates[0]
        end = dates[-1]

        if frequency == "weekly":
            freq = pd.DateOffset(weeks=1)
        elif frequency == "biweekly":
            freq = pd.DateOffset(weeks=2)
        else:  # monthly
            freq = pd.DateOffset(months=1)

        invest_dates = []
        current = start
        while current <= end:
            # 找最近的交易日
            invest_dates.append(current)
            current += freq

        return invest_dates

    def _enhanced_multiplier(self, match: pd.DataFrame) -> tuple:
        """
        根据估值调整买入倍数
        简化版: 用价格偏离均线的程度代替PE
        """
        multiplier = 1.0
        reason = "正常买入"

        close = match["close"]
        if len(close) < 252:
            return multiplier, reason

        # 当前价格 vs 250日均线
        ma250 = close.rolling(250).mean().iloc[-1]
        if pd.isna(ma250):
            return multiplier, reason

        current = close.iloc[-1]
        deviation = (current - ma250) / ma250 * 100

        if deviation < -30:
            multiplier = 3.0
            reason = f"极度低估(偏离{deviation:.0f}%) → 3倍买入"
        elif deviation < -20:
            multiplier = 2.0
            reason = f"低估(偏离{deviation:.0f}%) → 2倍买入"
        elif deviation < -10:
            multiplier = 1.5
            reason = f"偏低(偏离{deviation:.0f}%) → 1.5倍买入"
        elif deviation > 30:
            multiplier = 0.0
            reason = f"极度高估(偏离{deviation:.0f}%) → 暂停"
        elif deviation > 20:
            multiplier = 0.5
            reason = f"高估(偏离{deviation:.0f}%) → 减半"
        elif deviation > 10:
            multiplier = 0.8
            reason = f"偏高(偏离{deviation:.0f}%) → 0.8倍"

        return multiplier, reason

    def _calc_irr(self, invest_log: list, final_price: float) -> float:
        """估算 IRR"""
        if not invest_log:
            return 0
        # 简化：用总收益 / 平均投资年限
        total_invested = sum(log["amount"] for log in invest_log)
        total_value = sum(log["shares"] for log in invest_log) * final_price
        n = len(invest_log)
        if n < 1 or total_invested == 0:
            return 0
        avg_years = n / 12  # 假设月定投
        irr = ((total_value / total_invested) ** (1 / max(avg_years, 0.5)) - 1) * 100
        return irr


# ============================================================
# 3. 轮动 + 定投对比
# ============================================================

def compare_index_strategies(start_date: str = "2020-01-01"):
    """
    对比三种指数投资策略:
      1. 买入持有 (基准)
      2. 动量轮动
      3. 估值增强定投
    """
    from src.console import table

    print("\n" + "=" * 60)
    print("  📊 指数策略对比")
    print("=" * 60)

    results = []

    # 1. 买入持有沪深300
    data = get_index_data("000300", start_date=start_date)
    if not data.empty:
        first = data["close"].iloc[0]
        last = data["close"].iloc[-1]
        bh_return = (last / first - 1) * 100
        days = len(data)
        years = days / 252
        bh_annual = ((last / first) ** (1 / max(years, 0.01)) - 1) * 100
        results.append(["买入持有(沪深300)", f"{bh_return:+.1f}%", f"{bh_annual:+.1f}%", "-", "-"])

    # 2. 动量轮动
    try:
        rot = IndexRotation(top_k=2, lookback_days=20)
        rot_result = rot.run(start_date=start_date, initial_capital=100000)
        m = rot_result.get("metrics", {})
        results.append(["动量轮动(Top2/20日)", m.get("总收益率", "N/A"),
                        m.get("年化收益率", "N/A"), m.get("最大回撤", "N/A"),
                        m.get("胜率", "N/A")])
    except Exception as e:
        results.append(["动量轮动", f"失败: {e}", "", "", ""])

    # 3. 增强定投
    try:
        dca = DCABacktest("000300", "指数")
        dca_result = dca.run(amount_per_period=5000, enhanced=True,
                             start_date=start_date, verbose=False)
        dm = dca_result.get("metrics", {})
        results.append(["增强定投(沪深300)", dm.get("总收益率", "N/A"),
                        dm.get("年化收益", "N/A"), "-",
                        f"期数:{dm.get('定投期数','')}"])
    except Exception as e:
        results.append(["增强定投", f"失败: {e}", "", "", ""])

    table(
        ["策略", "总收益", "年化", "最大回撤", "备注"],
        results,
        title="指数策略对比"
    )

    return results
