"""AI Backtest Analyst — backtest results → structured assessment.

Reads backtest metrics and produces human-readable analysis.
LLM primary, rule-based fallback.  Analysis only — no auto-modification.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src.lxl_quantaxis.core.logging import get_logger

_log = get_logger("ai.backtest_analyzer")


# ═══════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════

@dataclass
class BacktestAssessment:
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    risk_warning: str = ""
    optimization_suggestions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "rule"

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "risk_warning": self.risk_warning,
            "optimization_suggestions": self.optimization_suggestions,
            "confidence": self.confidence,
            "source": self.source,
        }


# ═══════════════════════════════════════════════════════════
# Rule-based analysis
# ═══════════════════════════════════════════════════════════

def _parse_metric(metrics: dict, key: str) -> float:
    """Extract numeric metric from various string/number formats."""
    val = metrics.get(key, 0)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace("%", "").replace("+", "").replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _rule_analyze(metrics: dict) -> BacktestAssessment:
    """Rule-based backtest analysis using metric thresholds."""
    sharpe = _parse_metric(metrics, "夏普比率")
    total_ret = _parse_metric(metrics, "总收益率")
    win_rate = _parse_metric(metrics, "胜率")
    max_dd = _parse_metric(metrics, "最大回撤")
    trades = _parse_metric(metrics, "交易次数")

    a = BacktestAssessment(source="rule", confidence=0.35)

    # Summary
    if sharpe > 1.5:
        a.summary = f"优秀策略: 夏普{sharpe:.2f}, 收益{total_ret:+.1f}%。风险调整后收益显著。"
    elif sharpe > 0.5:
        a.summary = f"可行策略: 夏普{sharpe:.2f}, 收益{total_ret:+.1f}%。有一定alpha, 需优化。"
    elif sharpe > 0:
        a.summary = f"边际策略: 夏普{sharpe:.2f}, 收益勉强为正。建议改进因子条件。"
    else:
        a.summary = f"无效策略: 夏普{sharpe:.2f}为负, 因子缺乏预测力。"

    # Strengths
    if sharpe > 1.0:
        a.strengths.append(f"高夏普比率({sharpe:.2f}), 风险调整收益好")
    if win_rate > 55:
        a.strengths.append(f"胜率{win_rate:.1f}%, 方向判断准确")
    if total_ret > 20:
        a.strengths.append(f"总收益{total_ret:+.1f}%, 绝对回报可观")
    if trades > 20:
        a.strengths.append(f"交易{trades:.0f}次, 样本量充足")
    if not a.strengths:
        a.strengths.append("未发现显著优势")

    # Weaknesses
    if max_dd < -20:
        a.weaknesses.append(f"最大回撤{max_dd:.1f}%, 风险控制不足")
    if sharpe < 0.3:
        a.weaknesses.append(f"夏普{sharpe:.2f}过低, 风险调整后无优势")
    if win_rate < 45:
        a.weaknesses.append(f"胜率{win_rate:.1f}%偏低, 方向判断需改进")
    if trades < 10:
        a.weaknesses.append("交易次数过少, 统计意义有限")
    if not a.weaknesses:
        a.weaknesses.append("无明显弱点")

    # Risk warning
    if max_dd < -15:
        a.risk_warning = f"最大回撤{max_dd:.1f}%超过15%阈值, 实盘需降低仓位或加止损。"
    elif max_dd < -10:
        a.risk_warning = f"最大回撤{max_dd:.1f}%, 接近10%警戒线。"
    else:
        a.risk_warning = "回撤在可控范围内。"

    # Optimization suggestions
    if sharpe < 1.0:
        a.optimization_suggestions.append("尝试调整因子权重或增加过滤条件")
    if win_rate < 50:
        a.optimization_suggestions.append("考虑添加趋势过滤或市场状态检测")
    if max_dd < -15:
        a.optimization_suggestions.append("添加移动止损或降低单笔仓位")
    if trades < 15:
        a.optimization_suggestions.append("放宽入场条件以增加交易频率")
    if not a.optimization_suggestions:
        a.optimization_suggestions.append("当前参数已较优, 可考虑跨品种验证")

    return a


# ═══════════════════════════════════════════════════════════
# LLM-based analysis
# ═══════════════════════════════════════════════════════════

def _llm_analyze(metrics: dict, strategy_name: str = "") -> BacktestAssessment:
    """LLM-powered backtest analysis."""
    try:
        from src.ai.engine import LLMClient
        client = LLMClient()
        if not client.api_key:
            return _rule_analyze(metrics)

        prompt = f"""Analyze this quantitative strategy backtest result.

Strategy: {strategy_name or 'Unnamed'}
Metrics: {json.dumps({k: str(v) for k, v in metrics.items()}, ensure_ascii=False)}

Return ONLY a JSON object:
{{
  "summary": "one-sentence assessment in Chinese",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1"],
  "risk_warning": "key risk concern",
  "optimization_suggestions": ["suggestion 1", "suggestion 2"]
}}

Rules:
- Be specific about the numbers. Reference the actual metrics.
- Maximum 3 strengths and 3 weaknesses.
- Suggestions should be actionable.
- Do not include text outside the JSON."""

        response = client.ask(prompt, temperature=0.2)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return _rule_analyze(metrics)

        data = json.loads(json_match.group(0))
        return BacktestAssessment(
            summary=str(data.get("summary", ""))[:300],
            strengths=[str(s)[:200] for s in data.get("strengths", [])[:3]],
            weaknesses=[str(w)[:200] for w in data.get("weaknesses", [])[:3]],
            risk_warning=str(data.get("risk_warning", ""))[:200],
            optimization_suggestions=[
                str(s)[:200] for s in data.get("optimization_suggestions", [])[:3]
            ],
            confidence=0.70,
            source="llm",
        )
    except Exception as e:
        _log.warning(f"LLM analysis failed: {e}")
        return _rule_analyze(metrics)


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def analyze_backtest(
    metrics: dict,
    strategy_name: str = "",
    use_llm: bool = True,
) -> BacktestAssessment:
    """Analyze backtest results and produce structured assessment.

    Args:
        metrics: Dict of backtest metrics (from BacktestEngine.run())
        strategy_name: Strategy label for context
        use_llm: Try LLM first (falls back to rule-based)

    Returns:
        BacktestAssessment with structured analysis
    """
    if not metrics:
        return BacktestAssessment(
            summary="无回测数据", confidence=0.0, source="rule",
        )

    if use_llm:
        return _llm_analyze(metrics, strategy_name)

    return _rule_analyze(metrics)


def analyze_and_log(
    metrics: dict,
    strategy_name: str = "",
    factor_model: dict = None,
    use_llm: bool = True,
) -> BacktestAssessment:
    """Analyze AND persist to research notebook for strategy memory."""
    assessment = analyze_backtest(metrics, strategy_name, use_llm=use_llm)

    # Save to research notebook
    try:
        from src.lxl_quantaxis.research.notebook import create_note

        content = (
            f"Backtest Analysis for: {strategy_name}\n"
            f"Summary: {assessment.summary}\n"
            f"Strengths: {'; '.join(assessment.strengths)}\n"
            f"Weaknesses: {'; '.join(assessment.weaknesses)}\n"
            f"Risk: {assessment.risk_warning}\n"
            f"Suggestions: {'; '.join(assessment.optimization_suggestions)}\n"
            f"Source: {assessment.source}, Confidence: {assessment.confidence:.0%}"
        )
        create_note(
            title=f"Backtest Review: {strategy_name or 'Unknown'}",
            content=content,
            tags="backtest-review,ai-analysis",
        )
    except Exception as e:
        _log.warning(f"Failed to save assessment: {e}")

    return assessment
