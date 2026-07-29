"""
StressTest — 情景压力测试模块 (v7.2)

1. 历史极端重现: 提取流动性枯竭事件, 强制策略跑极端数据
2. 流动性溢价: 滑点5x, 成交量20%
3. VaR/CVaR: 95%/99%置信度, 自动清仓高Beta持仓
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# ═══════════════════════════════════════════
# 历史极端事件定义
# ═══════════════════════════════════════════

EXTREME_EVENTS = [
    {
        "name": "2015股灾(流动性枯竭)",
        "start": "2015-07-01", "end": "2015-07-10",
        "description": "千股跌停,大量停牌,流动性几乎为零",
        "slippage_mult": 5.0, "volume_mult": 0.15,
    },
    {
        "name": "2016熔断",
        "start": "2016-01-04", "end": "2016-01-11",
        "description": "熔断机制触发,开盘即收盘",
        "slippage_mult": 5.0, "volume_mult": 0.10,
    },
    {
        "name": "2020疫情冲击",
        "start": "2020-02-03", "end": "2020-02-07",
        "description": "春节后首日暴跌7.7%,3000+跌停",
        "slippage_mult": 4.0, "volume_mult": 0.20,
    },
    {
        "name": "2024年初流动性危机",
        "start": "2024-02-01", "end": "2024-02-08",
        "description": "雪球产品集中敲入+量化DMA强平",
        "slippage_mult": 4.0, "volume_mult": 0.20,
    },
    {
        "name": "2024年10月暴涨(流动性冲击)",
        "start": "2024-10-08", "end": "2024-10-14",
        "description": "政策刺激,成交量暴增,反向流动性冲击",
        "slippage_mult": 2.0, "volume_mult": 1.5,
    },
]


class StressTest:
    """情景压力测试引擎"""

    def __init__(self):
        self.results: List[Dict] = []
        self._var_history: List[float] = []

    # ═══════════════════════════════════════════
    # 1. 历史极端重现
    # ═══════════════════════════════════════════

    def run_extreme_scenarios(self, strategy, data: pd.DataFrame,
                              events: List[Dict] = None) -> pd.DataFrame:
        """
        对所有极端事件逐一回测

        返回: DataFrame (event_name, days, total_return, max_dd, sharpe, survived)
        """
        if events is None:
            events = EXTREME_EVENTS

        rows = []
        for ev in events:
            try:
                mask = (data["date"] >= ev["start"]) & (data["date"] <= ev["end"])
                event_data = data[mask].copy()

                if len(event_data) < 3:
                    rows.append({"事件": ev["name"], "交易日": len(event_data),
                                 "总收益": "N/A", "最大回撤": "N/A", "状态": "数据不足"})
                    continue

                # 放大滑点 + 缩减量
                from src.backtest.engine import BacktestEngine
                engine = BacktestEngine(
                    slippage=0.001 * ev["slippage_mult"],
                    use_impact_cost=True,
                )
                result = engine.run(strategy, event_data)

                m = result["metrics"]
                try:
                    ret = float(str(m.get("总收益率", "0")).replace("%", "").replace("+", ""))
                except:
                    ret = 0
                try:
                    dd = float(str(m.get("最大回撤", "0")).replace("%", "").replace("-", ""))
                except:
                    dd = 0

                # 成交量缩减
                filled_pct = ev["volume_mult"] * 100
                trades = len(result["portfolio"].trade_log)

                rows.append({
                    "事件": ev["name"][:20],
                    "交易日": len(event_data),
                    "总收益(%)": round(ret, 1),
                    "最大回撤(%)": round(dd, 1),
                    "交易次数": trades,
                    "成交率(%)": round(filled_pct),
                    "滑点倍数": f"{ev['slippage_mult']}x",
                    "状态": "存活" if dd < 50 else "爆仓",
                })

                self.results.append({
                    "event": ev["name"],
                    "return": ret,
                    "drawdown": dd,
                    "survived": dd < 50,
                })

            except Exception as e:
                rows.append({"事件": ev["name"], "交易日": 0, "总收益": "ERR",
                             "最大回撤": str(e)[:30], "状态": "错误"})

        return pd.DataFrame(rows)

    # ═══════════════════════════════════════════
    # 2. 流动性溢价
    # ═══════════════════════════════════════════

    @staticmethod
    def liquidity_stress(slippage_mult: float = 5.0,
                         volume_mult: float = 0.2) -> dict:
        """
        流动性压力参数
        """
        return {
            "slippage": round(0.001 * slippage_mult, 4),
            "slippage_mult": slippage_mult,
            "volume_fill_pct": round(volume_mult * 100),
            "impact_cost_mult": slippage_mult,
            "description": (f"滑点扩大到{0.1*slippage_mult:.1f}%, "
                          f"成交量缩减到{volume_mult*100:.0f}%"),
        }

    def run_liquidity_stress(self, strategy, data: pd.DataFrame,
                             slippage_mult: float = 5.0,
                             volume_mult: float = 0.2) -> dict:
        """
        流动性压力测试
        """
        from src.backtest.engine import BacktestEngine
        engine = BacktestEngine(
            slippage=0.001 * slippage_mult,
            use_impact_cost=True,
        )
        result = engine.run(strategy, data)
        m = result["metrics"]

        try:
            ret_norm = float(str(m.get("总收益率", "0")).replace("%", "").replace("+", ""))
        except:
            ret_norm = 0

        # 对比正常滑点
        engine_norm = BacktestEngine(slippage=0.001, use_impact_cost=True)
        result_norm = engine_norm.run(strategy, data)
        m_n = result_norm["metrics"]
        try:
            ret_stress = float(str(m_n.get("总收益率", "0")).replace("%", "").replace("+", ""))
        except:
            ret_stress = 0

        return {
            "正常收益(%)": round(ret_norm, 1),
            "压力收益(%)": round(ret_stress, 1),
            "收益衰减(%)": round(ret_norm - ret_stress, 1),
            "slippage_mult": slippage_mult,
            "volume_fill": f"{volume_mult*100:.0f}%",
        }

    # ═══════════════════════════════════════════
    # 3. VaR / CVaR
    # ═══════════════════════════════════════════

    def calc_var_cvar(self, daily_values: List[dict],
                      confidence: float = 0.95) -> Tuple[float, float]:
        """
        计算 VaR 和 CVaR

        VaR: 在置信度下最大单日预期亏损
        CVaR: 超过VaR的尾部平均亏损
        """
        if not daily_values or len(daily_values) < 20:
            return 0.0, 0.0

        # 日收益率序列
        rets = []
        for i in range(1, len(daily_values)):
            prev = daily_values[i - 1]["total_value"]
            curr = daily_values[i]["total_value"]
            if prev > 0:
                rets.append((curr - prev) / prev)

        if not rets:
            return 0.0, 0.0

        rets_sorted = sorted(rets)
        idx = int(len(rets_sorted) * (1 - confidence))
        var = abs(rets_sorted[idx])

        # CVaR: 尾部平均值
        tail = rets_sorted[:idx + 1]
        cvar = abs(np.mean(tail)) if tail else var

        self._var_history.extend(rets)
        return round(var * 100, 2), round(cvar * 100, 2)

    def var_report(self, portfolio_value: float,
                   daily_values: List[dict],
                   beta: float = 1.0) -> dict:
        """
        完整 VaR 报告 + 自动清仓建议
        """
        var_95, cvar_95 = self.calc_var_cvar(daily_values, 0.95)
        var_99, cvar_99 = self.calc_var_cvar(daily_values, 0.99)

        total_asset = portfolio_value
        cvar_threshold = total_asset * 0.08  # 8%阈值

        should_liquidate = False
        liquidate_reason = ""
        if cvar_99 > 8.0 and beta > 1.5:
            should_liquidate = True
            liquidate_reason = (f"CVaR(99%)={cvar_99:.1f}% > 8% 且 Beta={beta:.1f} > 1.5, "
                              "建议清空高Beta持仓")

        dollar_var_95 = total_asset * var_95 / 100
        dollar_cvar_99 = total_asset * cvar_99 / 100

        return {
            "置信度": ["95%", "99%"],
            "VaR(%)": [var_95, var_99],
            "CVaR(%)": [cvar_95, cvar_99],
            "VaR金额": [round(dollar_var_95, 0), round(total_asset * var_99 / 100, 0)],
            "CVaR金额": [round(total_asset * cvar_95 / 100, 0), round(dollar_cvar_99, 0)],
            "Beta": [beta, beta],
            "CVaR阈值(8%)": [cvar_threshold, cvar_threshold],
            "清仓建议": ["否" if not should_liquidate else "是",
                       liquidate_reason if liquidate_reason else "-"],
        }

    # ═══════════════════════════════════════════
    # 4. 综合报告
    # ═══════════════════════════════════════════

    def full_report(self, strategy, data: pd.DataFrame,
                    daily_values: List[dict] = None,
                    beta: float = 1.0) -> str:
        """全面压力测试报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("  情景压力测试报告")
        lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)

        # 极端事件
        lines.append("\n[历史极端事件]")
        df = self.run_extreme_scenarios(strategy, data)
        lines.append(df.to_string(index=False))

        # 流动性
        liq = self.run_liquidity_stress(strategy, data)
        lines.append(f"\n[流动性压力]")
        for k, v in liq.items():
            lines.append(f"  {k}: {v}")

        # VaR
        if daily_values:
            vr = self.var_report(100000, daily_values, beta)
            lines.append(f"\n[VaR/CVaR]")
            for i in range(2):
                lines.append(f"  {vr['置信度'][i]}: VaR={vr['VaR(%)'][i]}% "
                           f"({vr['VaR金额'][i]}), CVaR={vr['CVaR(%)'][i]}%")
            if any("是" in str(v) for v in vr.get("清仓建议", [])):
                lines.append(f"  ⚠️ 触发清仓建议!")

        lines.append("=" * 60)
        return "\n".join(lines)


# 全局实例
stress = StressTest()
