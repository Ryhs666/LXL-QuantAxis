"""
AI 量化助手 — 三个专职 AI 角色

  1. 交易复盘教练 — 分析交易记录，找出行为偏差
  2. 策略顾问     — 评估策略表现，给出优化建议
  3. 市场分析师   — 解读市场状态，生成每日简报
"""

import os, sys, json
from datetime import datetime
from typing import Optional, List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np

from src.ai.engine import (
    llm, QUANT_SYSTEM, TRADE_REVIEW_SYSTEM,
    STRATEGY_ADVISOR_SYSTEM, MARKET_WRITER_SYSTEM,
)
from src.models.trade import TradeRepository
from src.backtest.batch_runner import ResultDB
from src.backtest.data_feed import get_data_summary
from src.config import config


# ============================================================
# 1. AI 交易复盘教练
# ============================================================

class AITradeReviewer:
    """AI 复盘 — 分析交易行为"""

    def __init__(self):
        self.repo = TradeRepository()

    def _collect_trade_data(self) -> dict:
        """收集交易数据供 AI 分析"""
        pnl_list = self.repo.get_all_pnl()
        all_trades = self.repo.find_all(limit=500)
        positions = self.repo.find_open_positions()

        # 基础统计
        total_pnl = sum(p["net_pnl"] for p in pnl_list) if pnl_list else 0
        wins = [p for p in pnl_list if p["net_pnl"] > 0]
        losses = [p for p in pnl_list if p["net_pnl"] <= 0]
        win_rate = len(wins) / max(len(pnl_list), 1) * 100

        # 按市场
        by_market = {}
        for p in pnl_list:
            mkt = p.get("market", "未知")
            if mkt not in by_market:
                by_market[mkt] = {"count": 0, "pnl": 0, "wins": 0}
            by_market[mkt]["count"] += 1
            by_market[mkt]["pnl"] += p["net_pnl"]
            if p["net_pnl"] > 0:
                by_market[mkt]["wins"] += 1

        # 按标的
        by_symbol = {}
        for p in pnl_list:
            sym = p["symbol"]
            if sym not in by_symbol:
                by_symbol[sym] = {"count": 0, "pnl": 0}
            by_symbol[sym]["count"] += 1
            by_symbol[sym]["pnl"] += p["net_pnl"]

        # 最近交易
        recent = []
        for t in all_trades[:10]:
            pnl_info = ""
            if t.trade_type == "买入" and t.paired_trade_id:
                pnl = self.repo.calc_pnl(t.id)
                if pnl:
                    pnl_info = f"盈亏¥{pnl['net_pnl']:+,.2f}({pnl['pnl_pct']:+.1f}%)"
            recent.append({
                "日期": t.trade_date,
                "标的": f"{t.market} {t.symbol} {t.name}",
                "方向": t.direction,
                "类型": t.trade_type,
                "价格": f"¥{t.price:.2f}",
                "数量": t.quantity,
                "理由": t.reason or "无",
                "盈亏": pnl_info,
            })

        # 持仓
        holdings = []
        for p in positions:
            days = (datetime.now() - datetime.strptime(p.trade_date, "%Y-%m-%d")).days
            holdings.append({
                "标的": f"{p.symbol} {p.name}",
                "买入日": p.trade_date,
                "持仓天数": days,
                "成本": f"¥{p.price:.2f}",
                "数量": p.quantity,
                "理由": p.reason or "无",
            })

        return {
            "总交易": self.repo.count(),
            "已完成": len(pnl_list),
            "当前持仓": len(positions),
            "总盈亏": f"¥{total_pnl:+,.2f}",
            "胜率": f"{win_rate:.1f}%",
            "盈利笔数": len(wins),
            "亏损笔数": len(losses),
            "按市场": by_market,
            "按标的": by_symbol,
            "最近交易": recent,
            "当前持仓": holdings,
        }

    def review(self, focus: str = "全面") -> str:
        """生成 AI 复盘报告"""
        data = self._collect_trade_data()

        if data["总交易"] == 0:
            return "📭 暂无交易记录，先记几笔交易再来复盘吧。"

        prompt = f"""请分析以下交易数据，给出复盘建议。

## 交易概览
总交易: {data['总交易']} 笔 | 已完成: {data['已完成']} 笔 | 持仓: {data['当前持仓']} 只
总盈亏: {data['总盈亏']} | 胜率: {data['胜率']} | 盈{data['盈利笔数']}笔 / 亏{data['亏损笔数']}笔

## 按市场分布
{json.dumps(data['按市场'], ensure_ascii=False, indent=2)}

## 按标的盈亏
{json.dumps(data['按标的'], ensure_ascii=False, indent=2)}

## 最近交易
{json.dumps(data['最近交易'], ensure_ascii=False, indent=2)}

## 当前持仓
{json.dumps(data['当前持仓'], ensure_ascii=False, indent=2)}

## 分析要求
请从以下角度分析{focus}:
1. 是否存在追涨杀跌、过度交易等行为偏差？
2. 哪类交易最赚钱？哪类最亏钱？为什么？
3. 给出3条具体的、可操作的改进建议。
4. 【重要】一句话总结: 这个交易者最大的问题是什么？

⚠️ 如果数据量较少(<5笔)，请先鼓励用户多记录，再给出初步观察。"""

        return llm.ask(prompt, system=TRADE_REVIEW_SYSTEM)

    def quick_review(self, trade_id: int) -> str:
        """复盘单笔交易"""
        trade = self.repo.get_by_id(trade_id)
        if not trade:
            return f"找不到 ID={trade_id} 的交易"

        pnl_info = ""
        if trade.paired_trade_id:
            pnl = self.repo.calc_pnl(trade.id)
            if pnl:
                pnl_info = f"盈亏: ¥{pnl['net_pnl']:+,.2f} ({pnl['pnl_pct']:+.1f}%)"

        prompt = f"""复盘单笔交易:
- 日期: {trade.trade_date}
- 标的: {trade.market} {trade.symbol} {trade.name}
- 方向: {trade.direction} | 类型: {trade.trade_type}
- 价格: ¥{trade.price:.2f} × {trade.quantity}股
- 理由: {trade.reason or '未记录'}
- {pnl_info}
- 复盘笔记: {trade.review_notes or '未写'}
- 自评: {trade.review_score}分/5分

请:
1. 分析这笔交易的决策质量
2. 指出可能的认知偏差
3. 给出一条改进建议"""

        return llm.ask(prompt, system=TRADE_REVIEW_SYSTEM)


# ============================================================
# 2. AI 策略顾问
# ============================================================

class AIStrategyAdvisor:
    """AI 策略顾问 — 评估和优化策略"""

    def _collect_strategy_data(self) -> dict:
        """收集回测结果供 AI 分析"""
        db = ResultDB()
        results = db.query(limit=200)

        if not results:
            return {"回测数": 0}

        df = pd.DataFrame(results)

        best = df.nlargest(5, "sharpe")
        worst = df.nsmallest(5, "sharpe")

        # 按策略汇总
        by_strategy = {}
        for name, group in df.groupby("strategy"):
            by_strategy[name] = {
                "次数": len(group),
                "平均夏普": round(group["sharpe"].mean(), 2),
                "平均收益": round(group["total_return"].mean(), 1),
                "最佳收益": round(group["total_return"].max(), 1),
                "平均胜率": round(group["win_rate"].mean(), 1),
            }

        # 按标的汇总
        by_symbol = {}
        for name, group in df.groupby("symbol"):
            by_symbol[name] = {
                "次数": len(group),
                "平均夏普": round(group["sharpe"].mean(), 2),
                "最佳策略": group.loc[group["sharpe"].idxmax(), "strategy"]
                if len(group) > 0 else "",
            }

        top5 = [{
            "标的": r["symbol"], "策略": r["strategy"],
            "夏普": r["sharpe"], "收益": r["total_return"],
            "回撤": r["max_drawdown"], "胜率": r["win_rate"],
            "交易次数": r["trade_count"],
        } for r in best.to_dict(orient="records")]

        return {
            "回测数": len(results),
            "策略数": len(by_strategy),
            "标的数": len(by_symbol),
            "Top5": top5,
            "按策略": by_strategy,
            "按标的": by_symbol,
        }

    def analyze(self, strategy_name: str = None) -> str:
        """分析策略表现"""
        data = self._collect_strategy_data()

        if data["回测数"] == 0:
            return "📭 暂无回测数据，先跑几轮批量回测吧（菜单 3）。"

        focus = f"重点分析'{strategy_name}'策略" if strategy_name else "给出整体评估"

        prompt = f"""请分析以下回测数据，{focus}。

## 回测概况
{data['回测数']} 条记录 | {data['策略数']} 个策略 | {data['标的数']} 个标的

## TOP 5 最佳表现
{json.dumps(data['Top5'], ensure_ascii=False, indent=2)}

## 按策略统计
{json.dumps(data['按策略'], ensure_ascii=False, indent=2)}

## 按标的统计
{json.dumps(data['按标的'], ensure_ascii=False, indent=2)}

## 分析要求
1. 哪些策略在哪些标的上表现最好？有什么规律？
2. 是否存在过拟合风险（某个策略只在某个标的上好使）？
3. 给出策略组合建议（不同策略搭配使用）
4. 如果有明显问题，指出优化方向"""

        return llm.ask(prompt, system=STRATEGY_ADVISOR_SYSTEM)

    def suggest_params(self, strategy_name: str, current_params: dict = None) -> str:
        """建议参数优化方向"""
        data = self._collect_strategy_data()
        strategy_data = data.get("按策略", {}).get(strategy_name, {})

        prompt = f"""请为策略 '{strategy_name}' 建议参数优化方向。

## 当前表现
{json.dumps(strategy_data, ensure_ascii=False, indent=2) if strategy_data else '无数据'}

## 当前参数
{json.dumps(current_params, ensure_ascii=False, indent=2) if current_params else '使用默认值'}

请建议:
1. 哪些参数值得调优？方向是什么（增大/减小）？
2. 有没有过拟合的风险信号？
3. 建议添加什么过滤条件（成交量、趋势等）？"""

        return llm.ask(prompt, system=STRATEGY_ADVISOR_SYSTEM)

    def brainstorm(self, idea: str) -> str:
        """头脑风暴: 用自然语言描述策略想法，AI 帮你完善"""
        prompt = f"""交易者有一个策略想法，请帮忙完善:

"{idea}"

请:
1. 把这个想法转化成可量化的逻辑（具体条件、参数、阈值）
2. 指出这个策略可能的弱点或失效场景
3. 建议如何用回测验证这个想法
4. 是否有类似的经典策略可以参考？"""

        return llm.ask(prompt, system=STRATEGY_ADVISOR_SYSTEM)


# ============================================================
# 3. AI 市场分析师
# ============================================================

class AIMarketAnalyst:
    """AI 市场分析 — 生成简报"""

    def _collect_market_data(self) -> dict:
        """收集当前市场状态"""
        from src.backtest.data_feed import get_index_data, get_data_summary
        from src.backtest.batch_runner import ResultDB

        indices = {}
        for code in ["000300", "000016", "000905", "399006"]:
            try:
                df = get_index_data(code, start_date="2025-01-01")
                if df is not None and len(df) > 10:
                    close = df["close"]
                    ret_1m = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0
                    ret_3m = (close.iloc[-1] / close.iloc[-60] - 1) * 100 if len(close) >= 60 else 0
                    vol_trend = "放量" if df["volume"].iloc[-5:].mean() > df["volume"].iloc[-20:].mean() else "缩量"
                    indices[code] = {
                        "最新": round(close.iloc[-1], 2),
                        "近1月": f"{ret_1m:+.1f}%",
                        "近3月": f"{ret_3m:+.1f}%",
                        "量能": vol_trend,
                    }
            except Exception:
                pass

        # 缓存状态
        cache = get_data_summary()
        cache_info = f"{len(cache)} 个文件" if not cache.empty else "空"

        # 回测数据库
        db = ResultDB()
        summary = db.summary()

        return {
            "指数": indices,
            "数据缓存": cache_info,
            "回测记录": summary.get("总回测数", 0),
            "最佳策略": summary.get("最佳策略", "N/A"),
        }

    def daily_brief(self) -> str:
        """每日市场简报"""
        data = self._collect_market_data()

        if not data["指数"]:
            return "📭 暂无指数数据，先下载数据（菜单 7 → 1）。"

        prompt = f"""请根据以下数据，生成一份今日A股市场简报。

## 主要指数表现
{json.dumps(data['指数'], ensure_ascii=False, indent=2)}

## 系统状态
- 数据缓存: {data['数据缓存']}
- 历史回测: {data['回测记录']} 次
- 当前最优策略: {data['最佳策略']}

## 要求
格式如下:
```
📊 今日市场简报 ({datetime.now().strftime('%Y-%m-%d')})

【大势判断】
一句话判断当前是多头/空头/震荡市，给出理由。

【指数分化】
各指数强弱对比，谁领涨谁拖后腿，说明什么。

【量能分析】
放量还是缩量？意味着什么？

【风险提示】
当前最需要注意的风险点。

【操作建议】
一句话建议（进攻/防守/观望）。
```
⚠️ 声明: 仅供参考，不构成投资建议"""

        return llm.ask(prompt, system=MARKET_WRITER_SYSTEM)

    def explain(self, question: str) -> str:
        """自由提问：解释市场现象"""
        data = self._collect_market_data()

        prompt = f"""## 当前市场状态
{json.dumps(data['指数'], ensure_ascii=False, indent=2)}

## 用户提问
{question}

请用数据和逻辑回答，给出明确判断，不模棱两可。"""

        return llm.ask(prompt, system=MARKET_WRITER_SYSTEM)


# ============================================================
# 4. AI 自由对话
# ============================================================

class AIChat:
    """自由对话 — 跟 AI 聊量化"""

    def __init__(self):
        self.history = []

    def ask(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})
        if len(self.history) > 10:
            self.history = self.history[-10:]
        reply = llm.chat([{"role": "system", "content": QUANT_SYSTEM}] + self.history)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def ask_stream(self, message: str):
        """流式对话"""
        self.history.append({"role": "user", "content": message})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        full = ""
        for chunk in llm.chat_stream(
            [{"role": "system", "content": QUANT_SYSTEM}] + self.history
        ):
            print(chunk, end="", flush=True)
            full += chunk

        self.history.append({"role": "assistant", "content": full})
        print()
        return full

    def clear(self):
        self.history = []


# ============================================================
# 5. 配置向导
# ============================================================

def setup_ai_config():
    """引导用户配置 AI"""
    config_file = os.path.join(config.data_dir, "ai_config.json")

    print("\n  ╔══════════════════════════════════════╗")
    print("  ║     🤖 AI 功能配置向导                ║")
    print("  ╠══════════════════════════════════════╣")
    print("  ║                                      ║")
    print("  ║  支持所有 OpenAI 兼容 API:            ║")
    print("  ║  · ChatGPT (api.openai.com)          ║")
    print("  ║  · DeepSeek (api.deepseek.com)       ║")
    print("  ║  · 通义千问 (dashscope.aliyuncs.com)  ║")
    print("  ║  · 本地 Ollama (localhost:11434)      ║")
    print("  ║  · 其他兼容服务...                     ║")
    print("  ╚══════════════════════════════════════╝")

    api_key = input("\n  API Key (留空不修改): ").strip()
    base_url = input("  Base URL [https://api.openai.com/v1]: ").strip()
    model = input("  Model [gpt-4o]: ").strip()

    cfg = {}
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    if api_key:
        cfg["api_key"] = api_key
    if base_url:
        cfg["base_url"] = base_url
    if model:
        cfg["model"] = model

    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ 配置已保存到: {config_file}")

    # 测试连接
    test = input("\n  是否测试连接? (y/n): ").strip().lower()
    if test == "y":
        print("  测试中...")
        client = LLMClient(api_key=cfg.get("api_key"), base_url=cfg.get("base_url"),
                          model=cfg.get("model"))
        result = client.ask("回复'OK'即可")
        print(f"  {result}")


# 在 engine.py 底部引用
from src.ai.engine import LLMClient
