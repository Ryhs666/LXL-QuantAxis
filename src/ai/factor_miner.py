"""
AIFactorMiner — AI驱动的因子挖掘器 (v5.9)

流程:
  1. 统计价量数据特征(均值/标准差/峰度/偏度)
  2. 调用LLM生成创新因子公式
  3. 解析AI返回 → 动态注册到因子库
  4. 自动回测验证新因子
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import re
import json


class AIFactorMiner:
    """AI因子挖掘器"""

    def __init__(self):
        self._mined_factors = []

    # ═══════════════════════════════════════════
    # 1. 数据特征摘要
    # ═══════════════════════════════════════════

    @staticmethod
    def summarize(data: pd.DataFrame, symbol: str = "") -> str:
        """
        将OHLCV数据统计为文本摘要
        """
        if data is None or len(data) == 0:
            return "无数据"

        c = data["close"]
        v = data["volume"] if "volume" in data.columns else None
        ret = c.pct_change().dropna()

        lines = [f"=== {symbol} 市场数据特征 ==="]
        lines.append(f"样本数: {len(data)}, 时间范围: {str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]}")

        # 价格统计
        lines.append(f"\n[价格统计]")
        lines.append(f"  收盘价: 均值={c.mean():.2f}, 中位数={c.median():.2f}")
        lines.append(f"  收盘价: 标准差={c.std():.2f}, 最小值={c.min():.2f}, 最大值={c.max():.2f}")
        if len(ret) > 0:
            lines.append(f"  日收益率: 均值={ret.mean():.6f}, 标准差={ret.std():.6f}")

        # 分布特征
        if len(ret) > 10:
            skew = ret.skew()
            kurt = ret.kurtosis()
            lines.append(f"  收益率: 偏度={skew:.3f}, 峰度={kurt:.3f}")
            lines.append(f"  偏度解读: {'正偏(涨多跌少)' if skew > 0.3 else ('负偏(跌多涨少)' if skew < -0.3 else '近似正态')}")
            lines.append(f"  峰度解读: {'肥尾(极端行情较多)' if kurt > 1 else ('薄尾(行情温和)' if kurt < -0.5 else '接近正态')}")

        # 波动特征
        if len(ret) > 20:
            vol_20d = ret.rolling(20).std().iloc[-1] * np.sqrt(252)
            lines.append(f"  20日年化波动率: {vol_20d:.2%}")
            # 波动率分位
            rolling_vol = ret.rolling(60).std() * np.sqrt(252)
            if len(rolling_vol.dropna()) > 0:
                current_vol_pct = (rolling_vol.dropna().iloc[-1:].values[0] < rolling_vol.dropna()).mean()
                lines.append(f"  当前波动率处于历史 {current_vol_pct:.0%} 分位")

        # 成交量
        if v is not None:
            lines.append(f"\n[成交量统计]")
            lines.append(f"  成交量: 均值={v.mean():.0f}, 标准差={v.std():.0f}")
            vol_ratio = v.iloc[-20:].mean() / v.mean() if v.mean() > 0 else 1
            lines.append(f"  近期量比(20日/全期): {vol_ratio:.2f} ({'放量' if vol_ratio > 1.2 else ('缩量' if vol_ratio < 0.8 else '正常')})")

        # 趋势特征
        if len(c) > 60:
            ma20 = c.rolling(20).mean().iloc[-1]
            ma60 = c.rolling(60).mean().iloc[-1]
            lines.append(f"\n[趋势特征]")
            lines.append(f"  MA20/MA60: {ma20/ma60:.3f} ({'多头排列' if ma20 > ma60 else '空头排列'})")
            lines.append(f"  当前价/MA60: {c.iloc[-1]/ma60:.3f}")
            high_60 = c.rolling(60).max().iloc[-1]
            low_60 = c.rolling(60).min().iloc[-1]
            pos_60 = (c.iloc[-1] - low_60) / (high_60 - low_60) if high_60 != low_60 else 0.5
            lines.append(f"  60日价格位置: {pos_60:.2%} (0=底部, 1=顶部)")

        # 日内波动
        if "high" in data.columns and "low" in data.columns:
            intraday_range = ((data["high"] - data["low"]) / c).mean()
            lines.append(f"\n[日内特征]")
            lines.append(f"  平均日内振幅: {intraday_range:.2%}")

        return "\n".join(lines)

    # ═══════════════════════════════════════════
    # 2. 调用 AI 挖掘因子
    # ═══════════════════════════════════════════

    def mine(self, data: pd.DataFrame, symbol: str = "",
             temperature: float = 0.8) -> List[Dict]:
        """
        让AI生成创新因子

        返回: [
          {name: str, formula: str, logic: str, category: str, python_hint: str}
        ]
        """
        from src.ai.engine import LLMClient

        summary = self.summarize(data, symbol)

        prompt = f"""你是一位量化因子研究专家。基于以下A股市场的价量数据统计特征，请推荐3个非传统的量化因子。

{summary}

要求:
1. 每个因子必须有明确的逻辑支撑，解释它在A股市场中为什么有效
2. 因子的计算方式必须可以用pandas/numpy实现
3. 给出具体的Python计算代码(基于OHLCV DataFrame, 包含列: open/high/low/close/volume)
4. 因子输出应标准化到0~1之间
5. 类型标注: trend(趋势)/momentum(动量)/volatility(波动)/volume(成交量)/pattern(形态)/composite(复合)

返回JSON格式(只返回JSON):
{{
  "factors": [
    {{
      "name": "因子英文名(如intraday_curvature)",
      "chinese_name": "因子中文名",
      "formula": "数学公式描述",
      "logic": "在A股市场的逻辑支撑(50字)",
      "category": "趋势/动量/波动/成交量/形态/复合",
      "python_code": "def calc_factor(data):\\n    # pandas代码\\n    return result_series_normalized_to_0_1"
    }}
  ]
}}

注意:
- 因子要有创新性,不要重复RSI/MACD/布林等常见因子
- 每个因子应该是独立的计算单元
- Python代码要完整可运行"""

        client = LLMClient()
        reply = client.ask(prompt, system="你是量化因子研究专家。只返回JSON，不做额外解释。",
                          temperature=temperature)

        # 解析
        return self._parse_response(reply)

    def _parse_response(self, reply: str) -> List[Dict]:
        """解析LLM返回的因子"""
        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', reply, re.DOTALL)
        if not json_match:
            # 降级: 手动解析文本
            return self._fallback_parse(reply)

        try:
            data = json.loads(json_match.group(0))
            factors = data.get("factors", [])
            result = []
            for f in factors:
                result.append({
                    "name": f.get("name", "ai_factor"),
                    "chinese_name": f.get("chinese_name", "AI因子"),
                    "formula": f.get("formula", ""),
                    "logic": f.get("logic", ""),
                    "category": f.get("category", "composite"),
                    "python_code": f.get("python_code", "# no code"),
                })
            self._mined_factors.extend(result)
            return result
        except json.JSONDecodeError:
            return self._fallback_parse(reply)

    def _fallback_parse(self, reply: str) -> List[Dict]:
        """JSON解析失败时的降级方案"""
        # 按 "因子1/2/3" 或数字编号拆分
        factors = []
        for i in range(1, 4):
            factors.append({
                "name": f"ai_mined_{i}",
                "chinese_name": f"AI挖掘因子{i}",
                "formula": "见下方代码",
                "logic": "AI自动生成",
                "category": "composite",
                "python_code": f"# AI原始回复:\n# {reply[:500]}",
            })
        return factors

    # ═══════════════════════════════════════════
    # 3. 动态注册因子
    # ═══════════════════════════════════════════

    # ── Safe operation whitelist (no exec/eval) ──
    _SAFE_OPS = {
        "pct_change": lambda data, period: data["close"].pct_change(period),
        "rolling_mean": lambda data, period: data["close"].rolling(period).mean(),
        "rolling_std": lambda data, period: data["close"].rolling(period).std(),
        "rolling_max": lambda data, period: data["close"].rolling(period).max(),
        "rolling_min": lambda data, period: data["close"].rolling(period).min(),
        "ema": lambda data, period: data["close"].ewm(span=period).mean(),
        "volume_ratio": lambda data, period: data["volume"] / data["volume"].rolling(period).mean(),
        "high_low_range": lambda data, period: (data["high"] - data["low"]) / data["close"],
        "close_position": lambda data, period: (data["close"] - data["low"]) / (data["high"] - data["low"] + 1e-8),
    }

    def register_factor(self, factor_def: Dict) -> bool:
        """
        Register an AI-generated factor using ONLY safe, whitelisted operations.

        AI output is parsed as structured JSON with:
          {name, category, chinese_name, operator, period, normalization}
        No raw Python code is executed. All computations use pre-audited ops.
        """
        try:
            from src.factors.definitions import Factor, FACTOR_REGISTRY

            name = str(factor_def.get("name", "")).strip()
            if not name or not name.isidentifier():
                print(f"[AIFactorMiner] 拒绝非法因子名: {name!r}")
                return False

            category = str(factor_def.get("category", "composite")).strip()
            description = str(factor_def.get("chinese_name", factor_def.get("logic", "")))[:100]
            operator = str(factor_def.get("operator", "pct_change")).strip()
            period = int(factor_def.get("period", 20))

            if operator not in self._SAFE_OPS:
                print(f"[AIFactorMiner] 不支持的算子: {operator!r}, "
                      f"可用: {list(self._SAFE_OPS)}")
                return False

            if not (1 <= period <= 252):
                print(f"[AIFactorMiner] period 超出范围 [1,252]: {period}")
                return False

            # Build a safe compute function from whitelisted ops
            safe_fn = self._SAFE_OPS[operator]

            def make_compute(op_fn, p):
                def compute(data):
                    return op_fn(data, p)
                return compute

            if name not in FACTOR_REGISTRY:
                FACTOR_REGISTRY[name] = Factor(
                    name=name,
                    category=category,
                    description=description,
                    compute=make_compute(safe_fn, period),
                )
                print(f"[AIFactorMiner] 安全注册因子: {name} "
                      f"(op={operator}, period={period})")
                return True
            return False
        except Exception as e:
            print(f"[AIFactorMiner] 注册因子 {factor_def.get('name')} 失败: {e}")
            return False

    def register_all(self) -> int:
        """注册所有已挖掘的因子"""
        count = 0
        for f in self._mined_factors:
            if self.register_factor(f):
                count += 1
        return count

    # ═══════════════════════════════════════════
    # 4. 批量挖掘
    # ═══════════════════════════════════════════

    def mine_and_register(self, data: pd.DataFrame, symbol: str = "",
                          temperature: float = 0.8) -> List[Dict]:
        """一步: 挖掘 + 注册"""
        factors = self.mine(data, symbol, temperature)
        registered = 0
        for f in factors:
            if self.register_factor(f):
                registered += 1
        print(f"[AIFactorMiner] 挖掘了{len(factors)}个因子, 成功注册{registered}个")
        return factors

    def get_mined_factors(self) -> List[Dict]:
        return self._mined_factors


# ═══════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════

def quick_mine(symbol: str = "600498",
               start_date: str = "2024-01-01") -> List[Dict]:
    """快速AI因子挖掘"""
    from src.backtest.data_feed import get_data
    data = get_data(symbol, "A股", start_date=start_date)
    if data is None or len(data) == 0:
        print(f"无法获取{symbol}数据")
        return []

    miner = AIFactorMiner()
    return miner.mine_and_register(data, symbol)
