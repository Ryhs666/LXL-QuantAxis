"""AI Research Report Generator — institutional-style investment reports.

Takes all pipeline outputs (thesis, factor model, strategy, backtest,
portfolio assessment) and produces structured Markdown and HTML reports.
PDF interface reserved for future.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.lxl_quantaxis.core.logging import get_logger

_log = get_logger("research.report_generator")


# ═══════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════

@dataclass
class ResearchReport:
    title: str = ""
    subtitle: str = ""
    date: str = ""
    author: str = "LXL QuantAxis"

    # Sections
    investment_summary: str = ""
    thesis: str = ""
    factor_analysis: str = ""
    strategy_analysis: str = ""
    backtest_analysis: str = ""
    portfolio_analysis: str = ""
    risk_section: str = ""
    conclusion: str = ""

    # Metadata
    symbol: str = ""
    tags: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render as institutional Markdown report."""
        lines = [
            f"# {self.title}",
            f"*{self.subtitle}*" if self.subtitle else "",
            f"",
            f"**日期**: {self.date} | **作者**: {self.author}",
            f"**标的**: {self.symbol}" if self.symbol else "",
            f"**标签**: {', '.join(self.tags)}" if self.tags else "",
            f"",
            f"---",
            f"",
            f"## 1. 投资摘要",
            self.investment_summary or "暂无摘要",
            f"",
            f"## 2. 投资逻辑",
            self.thesis or "暂无投资逻辑",
            f"",
            f"## 3. 量化因子分析",
            self.factor_analysis or "暂无因子分析",
            f"",
            f"## 4. 策略构建",
            self.strategy_analysis or "暂无策略分析",
            f"",
            f"## 5. 历史回测",
            self.backtest_analysis or "暂无回测数据",
            f"",
            f"## 6. 组合分析",
            self.portfolio_analysis or "暂无组合分析",
            f"",
            f"## 7. 风险分析",
            self.risk_section or "暂无风险分析",
            f"",
            f"## 8. 结论",
            self.conclusion or "暂无结论",
            f"",
            f"---",
            f"*本报告由 LXL·QuantAxis V2.0 自动生成，仅供参考，不构成投资建议。*",
        ]
        return "\n".join(lines)

    def to_html(self) -> str:
        """Render as styled HTML report."""
        md = self.to_markdown()
        # Simple Markdown → HTML conversion for key elements
        html_parts = []
        in_code = False
        for line in md.split("\n"):
            if line.startswith("```"):
                in_code = not in_code
                html_parts.append("<pre><code>" if not in_code else "</code></pre>")
                continue
            if in_code:
                html_parts.append(line)
                continue
            if line.startswith("# "):
                html_parts.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_parts.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("---"):
                html_parts.append("<hr>")
            elif line.startswith("*"):
                html_parts.append(f"<em>{line[1:-1] if line.endswith('*') else line[1:]}</em>")
            elif line.strip():
                html_parts.append(f"<p>{line}</p>")
            else:
                html_parts.append("<br>")

        body = "\n".join(html_parts)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<title>{self.title}</title>
<style>
body{{font-family:'Segoe UI',system-ui,sans-serif;max-width:800px;margin:40px auto;
     padding:0 20px;background:#fff;color:#1a1a2e;line-height:1.8}}
h1{{color:#1a3a5c;border-bottom:2px solid #3b82f6;padding-bottom:8px}}
h2{{color:#2d5a87;margin-top:32px}}
hr{{border:0;border-top:1px solid #e2e8f0;margin:24px 0}}
p{{margin:8px 0}}
em{{color:#64748b}}
pre{{background:#f1f5f9;padding:12px;border-radius:6px}}
</style></head><body>{body}</body></html>"""

    def save_markdown(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        return path

    def save_html(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_html())
        return path

    def save(self, dir_path: str = "") -> dict[str, str]:
        """Save both formats. Returns {markdown_path, html_path}."""
        import os
        os.makedirs(dir_path, exist_ok=True)
        safe_name = self.title.replace(" ", "_").replace("/", "_")[:60]
        md_path = os.path.join(dir_path, f"{safe_name}.md")
        html_path = os.path.join(dir_path, f"{safe_name}.html")
        return {
            "markdown": self.save_markdown(md_path),
            "html": self.save_html(html_path),
        }


# ═══════════════════════════════════════════════════════════
# Report builder
# ═══════════════════════════════════════════════════════════

def _safe_get(obj, attr, default=""):
    """Safely get attribute or dict key."""
    if obj is None:
        return default
    if hasattr(obj, attr):
        return str(getattr(obj, attr) or default)
    if isinstance(obj, dict):
        return str(obj.get(attr, default))
    return default


def _format_metric(val, fmt=".2f") -> str:
    """Format a metric value safely."""
    try:
        v = float(str(val).replace("%", "").replace("+", ""))
        return f"{v:{fmt}}"
    except (ValueError, TypeError):
        return str(val)


def generate_report(
    symbol: str = "",
    thesis=None,
    factor_model=None,
    strategy_spec=None,
    backtest_metrics: dict = None,
    backtest_assessment=None,
    portfolio_assessment=None,
    title: str = "",
) -> ResearchReport:
    """Generate a complete institutional research report from pipeline outputs.

    Args:
        symbol: Stock code
        thesis: InvestmentThesis object
        factor_model: FactorModel object
        strategy_spec: StrategySpec object
        backtest_metrics: Dict of backtest metrics
        backtest_assessment: BacktestAssessment object
        portfolio_assessment: PortfolioAssessment object
        title: Custom title

    Returns:
        ResearchReport ready for Markdown/HTML rendering
    """
    report = ResearchReport(
        title=title or f"量化研究: {symbol}",
        subtitle=f"LXL·QuantAxis V2.0 自动生成 | {datetime.now().strftime('%Y-%m-%d')}",
        date=datetime.now().strftime("%Y-%m-%d"),
        symbol=symbol,
    )

    # 1. Investment Summary
    thesis_text = _safe_get(thesis, "core_argument") or _safe_get(thesis, "investment_thesis")
    conviction = _safe_get(thesis, "conviction") or "medium"
    report.investment_summary = (
        f"本报告对 **{symbol}** 进行量化分析。\n\n"
        f"**核心观点**: {thesis_text or '待补充'}\n"
        f"**确信度**: {conviction}"
    )

    # 2. Thesis
    report.thesis = (
        f"**看多理由**: {_safe_get(thesis, 'bullish_reasons') or _safe_get(thesis, 'bull_case') or '待补充'}\n\n"
        f"**看空理由**: {_safe_get(thesis, 'bearish_reasons') or _safe_get(thesis, 'bear_case') or '待补充'}\n\n"
        f"**关键风险**: {_safe_get(thesis, 'key_risks') or _safe_get(thesis, 'risk') or '待补充'}"
    )
    report.tags.append("thesis")

    # 3. Factor Analysis
    if factor_model:
        theme = _safe_get(factor_model, "theme")
        factors = getattr(factor_model, "factors", [])
        if hasattr(factor_model, "to_dict"):
            factors = factor_model.to_dict().get("factors", [])
        if factors:
            lines = [f"**主题**: {theme}"]
            lines.append("")
            lines.append("| 因子 | 权重 | 理由 |")
            lines.append("|------|------|------|")
            for f in factors[:8]:
                name = f.get("name", "") if isinstance(f, dict) else getattr(f, "name", "")
                weight = f.get("weight", 0) if isinstance(f, dict) else getattr(f, "weight", 0)
                reason = f.get("reason", "") if isinstance(f, dict) else getattr(f, "reason", "")
                lines.append(f"| {name} | {weight:.1%} | {reason} |")
            report.factor_analysis = "\n".join(lines)
            report.tags.append("factor-model")
    if not report.factor_analysis:
        report.factor_analysis = "暂无因子模型数据。"

    # 4. Strategy Analysis
    if strategy_spec:
        name = _safe_get(strategy_spec, "name")
        entry = _safe_get(strategy_spec, "entry_rule")
        exit_r = _safe_get(strategy_spec, "exit_rule")
        report.strategy_analysis = (
            f"**策略名称**: {name}\n\n"
            f"**入场规则**: `{entry}`\n"
            f"**离场规则**: `{exit_r}`\n"
        )
        report.tags.append("strategy")
    if not report.strategy_analysis:
        report.strategy_analysis = "暂无策略构建数据。"

    # 5. Backtest Analysis
    if backtest_metrics:
        lines = ["| 指标 | 数值 |", "|------|------|"]
        key_metrics = ["夏普比率", "总收益率", "胜率", "最大回撤", "交易次数",
                       "年化收益率", "索提诺比率", "卡尔玛比率"]
        for k in key_metrics:
            if k in (backtest_metrics or {}):
                lines.append(f"| {k} | {_format_metric(backtest_metrics[k])} |")
        report.backtest_analysis = "\n".join(lines)
        report.tags.append("backtest")

        if backtest_assessment:
            summary = _safe_get(backtest_assessment, "summary")
            strengths = getattr(backtest_assessment, "strengths", [])
            weaknesses = getattr(backtest_assessment, "weaknesses", [])
            report.backtest_analysis += (
                f"\n\n**评估**: {summary}\n"
                f"**优势**: {'; '.join(strengths) if strengths else '无'}\n"
                f"**不足**: {'; '.join(weaknesses) if weaknesses else '无'}"
            )
    if not report.backtest_analysis:
        report.backtest_analysis = "暂无回测数据。"

    # 6. Portfolio Analysis
    if portfolio_assessment:
        alloc = getattr(portfolio_assessment, "allocation", [])
        if hasattr(portfolio_assessment, "to_dict"):
            alloc = portfolio_assessment.to_dict().get("allocation", [])
        if alloc:
            lines = ["| 策略 | 权重 | 预期收益 | 风险 |", "|------|------|----------|------|"]
            for a in alloc:
                lines.append(
                    f"| {a.get('name','')} | {a.get('weight',0):.1%} | "
                    f"{a.get('expected_return',0):.1f}% | {a.get('risk',0):.1f}% |"
                )
            report.portfolio_analysis = "\n".join(lines)
            report.tags.append("portfolio")
    if not report.portfolio_analysis:
        report.portfolio_analysis = "暂无组合分析数据。"

    # 7. Risk
    risk_parts = []
    if backtest_metrics:
        dd = _safe_get(backtest_metrics, "最大回撤")
        if dd:
            risk_parts.append(f"- 最大回撤: {_format_metric(dd)}")
    if portfolio_assessment:
        warnings = _safe_get(portfolio_assessment, "risk_warning")
        if warnings:
            risk_parts.append(f"- 组合风险: {warnings}")
    if backtest_assessment:
        rw = _safe_get(backtest_assessment, "risk_warning")
        if rw:
            risk_parts.append(f"- 策略风险: {rw}")
    report.risk_section = "\n".join(risk_parts) if risk_parts else "暂无风险分析数据。"

    # 8. Conclusion
    conclusion_parts = []
    if backtest_assessment:
        conclusion_parts.append(_safe_get(backtest_assessment, "summary"))
    if portfolio_assessment:
        recs = getattr(portfolio_assessment, "recommendations", [])
        if recs:
            conclusion_parts.append("**建议**: " + "; ".join(recs[:3]))
    report.conclusion = "\n\n".join(conclusion_parts) if conclusion_parts else "待补充结论。"

    return report
