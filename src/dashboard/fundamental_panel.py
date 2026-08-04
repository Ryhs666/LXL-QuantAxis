"""
Fundamental Data Panel — 基本面数据可视化

生成 PE/PB/ROE 历史折线图和财务报表摘要。
"""

import json
import os
from datetime import datetime


def build_fundamental_data_api(symbol: str) -> dict:
    """构建基本面数据 JSON API"""
    try:
        from src.data.financials import financial_db
        pe_series = financial_db.get_pe_series(symbol)
        pb_series = financial_db.get_pb_series(symbol)
        roe_series = financial_db.get_roe_series(symbol)
    except ImportError:
        pe_series = pb_series = roe_series = None

    return {
        "symbol": symbol,
        "pe_history": _df_to_list(pe_series, "pe") if pe_series is not None else [],
        "pb_history": _df_to_list(pb_series, "pb") if pb_series is not None else [],
        "roe_history": _df_to_list(roe_series, "roe") if roe_series is not None else [],
        "generated_at": datetime.now().isoformat(),
    }


def build_fundamental_panel_html(symbol: str) -> str:
    """生成基本面面板 HTML (Plotly)"""
    data = build_fundamental_data_api(symbol)

    # 生成三个 Plotly 图表的 JSON
    charts = []
    for label, history, y_label, color in [
        ("PE 历史", data["pe_history"], "PE", "#3b82f6"),
        ("PB 历史", data["pb_history"], "PB", "#8b5cf6"),
        ("ROE 历史", data["roe_history"], "ROE (%)", "#10b981"),
    ]:
        if history:
            dates = [h["date"] for h in history]
            values = [h["value"] for h in history]
            fig_json = _make_line_chart_json(dates, values, label, y_label, color)
            charts.append({"title": label, "figure_json": fig_json})

    return _wrap_html(f"基本面分析 — {symbol}", charts)


def _df_to_list(df, col: str) -> list:
    """DataFrame → [{date, value}]"""
    if df is None or df.empty:
        return []
    try:
        return [
            {"date": str(r["date"])[:10], "value": float(r[col])}
            for _, r in df.iterrows()
        ]
    except Exception:
        return []


def _make_line_chart_json(dates: list, values: list, title: str,
                          y_label: str, color: str) -> str:
    """生成 Plotly 折线图 JSON"""
    fig = {
        "data": [{
            "x": dates, "y": values,
            "type": "scatter", "mode": "lines",
            "line": {"color": color, "width": 2},
            "name": y_label,
        }],
        "layout": {
            "title": {"text": title, "font": {"color": "#f1f5f9"}},
            "xaxis": {"title": "", "gridcolor": "#1e293b", "color": "#94a3b8"},
            "yaxis": {"title": y_label, "gridcolor": "#1e293b", "color": "#94a3b8"},
            "paper_bgcolor": "#0b0f1a",
            "plot_bgcolor": "#0b0f1a",
            "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
        },
    }
    return json.dumps(fig)


def _wrap_html(title: str, charts: list) -> str:
    """包裹为完整 HTML"""
    chart_divs = ""
    for i, c in enumerate(charts):
        chart_divs += f"""
        <div class="chart-container" style="margin-bottom:24px;">
            <h3 style="color:#94a3b8;margin-bottom:8px;">{c['title']}</h3>
            <div id="chart_{i}" style="width:100%;height:320px;"></div>
            <script>
                Plotly.newPlot('chart_{i}', {c['figure_json']}['data'], {c['figure_json']}['layout'],
                    {{responsive: true, displayModeBar: false}});
            </script>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
    body {{ background: #060912; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;
           margin: 0; padding: 20px; }}
    .chart-container {{ background: #111827; padding: 16px; border-radius: 8px; }}
</style>
</head><body>
<h1 style="color:#3b82f6;">{title}</h1>
{chart_divs}
</body></html>"""
