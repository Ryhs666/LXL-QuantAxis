"""
Alpha Memory Dashboard — 信号记忆可视化

展示因子胜率、市场状态表现、IC衰减时间线、最近信号表。
"""

import json
from datetime import datetime


def build_alpha_data_api() -> dict:
    """构建 Alpha 记忆数据 JSON API"""
    data = {
        "win_rate_by_factor": {},
        "regime_matrix": {},
        "factor_health": {},
        "recent_signals": [],
        "source_stats": {},
    }

    try:
        from src.ai.alpha_store import alpha_store
        data["win_rate_by_factor"] = alpha_store.get_win_rate_by_factor(days=90)
        data["regime_matrix"] = alpha_store.get_regime_performance_matrix(days=180)
        data["factor_health"] = alpha_store.get_factor_health()
        data["recent_signals"] = alpha_store.get_recent(limit=20)
        data["source_stats"] = alpha_store.get_source_stats(days=90)
    except ImportError:
        pass

    data["generated_at"] = datetime.now().isoformat()
    return data


def build_alpha_panel_html() -> str:
    """生成 Alpha 记忆面板 HTML"""
    data = build_alpha_data_api()

    # 因子胜率表
    factor_rows = ""
    for name, stats in sorted(data["win_rate_by_factor"].items(),
                               key=lambda x: x[1].get("total", 0), reverse=True)[:15]:
        wr = stats.get("win_rate", 0)
        color = "#10b981" if wr >= 0.5 else "#ef4444"
        factor_rows += f"""
        <tr>
            <td style="color:#f1f5f9;">{name}</td>
            <td>{stats.get('total', 0)}</td>
            <td style="color:{color};">{wr:.0%}</td>
            <td>{stats.get('avg_pnl_pct', 0):.2%}</td>
        </tr>"""

    # 市场状态矩阵
    regime_labels = {0: "高波动上涨", 1: "高波动下跌", 2: "低波动震荡", 3: "高波动反转"}
    regime_rows = ""
    for rid, stats in sorted(data["regime_matrix"].items()):
        wr = stats.get("win_rate", 0)
        color = "#10b981" if wr >= 0.5 else "#ef4444"
        regime_rows += f"""
        <tr>
            <td style="color:#f1f5f9;">{regime_labels.get(rid, str(rid))}</td>
            <td>{stats.get('total_signals', 0)}</td>
            <td style="color:{color};">{wr:.0%}</td>
            <td>{stats.get('avg_pnl_pct', 0):.2%}</td>
            <td style="color:#94a3b8;">{', '.join(stats.get('best_factors', []))}</td>
        </tr>"""

    # 最近信号表
    signal_rows = ""
    for s in data["recent_signals"][:10]:
        outcome_color = {"win": "#10b981", "loss": "#ef4444"}.get(
            s.get("outcome", ""), "#94a3b8")
        signal_rows += f"""
        <tr>
            <td>{s.get('date', '')}</td>
            <td>{s.get('symbol', '')}</td>
            <td>{s.get('factor_name', '')}</td>
            <td>{s.get('source', '')}</td>
            <td style="color:{outcome_color};">{s.get('outcome', '-')}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Alpha Memory Dashboard</title>
<style>
    body {{ background: #060912; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;
           margin: 0; padding: 20px; }}
    h1 {{ color: #3b82f6; }}
    h2 {{ color: #8b5cf6; margin-top: 32px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
    th {{ background: #1a2332; color: #94a3b8; padding: 8px 12px; text-align: left;
          font-size: 12px; font-weight: 600; }}
    td {{ padding: 6px 12px; border-bottom: 1px solid #1e293b; font-size: 13px;
          color: #cbd5e1; }}
    tr:hover {{ background: #0f172a; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    .card {{ background: #111827; padding: 16px; border-radius: 8px; }}
</style>
</head><body>
<h1>Alpha Memory Dashboard</h1>
<p style="color:#475569;">Generated: {data['generated_at']}</p>

<div class="grid">
    <div class="card">
        <h2>因子胜率 TOP 15</h2>
        <table>
            <tr><th>因子</th><th>信号数</th><th>胜率</th><th>平均PnL</th></tr>
            {factor_rows}
        </table>
    </div>
    <div class="card">
        <h2>市场状态表现矩阵</h2>
        <table>
            <tr><th>状态</th><th>信号数</th><th>胜率</th><th>平均PnL</th><th>最佳因子</th></tr>
            {regime_rows}
        </table>
    </div>
</div>

<div class="card" style="margin-top:24px;">
    <h2>最近信号</h2>
    <table>
        <tr><th>日期</th><th>股票</th><th>因子</th><th>来源</th><th>结果</th></tr>
        {signal_rows}
    </table>
</div>
</body></html>"""
