"""
Macro Dashboard Panel — 宏观数据可视化

展示 CPI/PPI/PMI、LPR、美联储利率等宏观指标。
"""

import json
from datetime import datetime


def build_macro_data_api() -> dict:
    """构建宏观数据 JSON API"""
    indicators = {}
    try:
        from src.data.macro_fetchers import get_macro_data
        for code in ["CN_CPI_YOY", "CN_PPI_YOY", "CN_PMI", "CN_LPR_1Y",
                      "US_CPI_YOY", "US_FED_FUNDS", "US_UNEMPLOYMENT", "US_10Y_YIELD"]:
            try:
                df = get_macro_data(code, start_date="2020-01-01")
                if df is not None and not df.empty:
                    indicators[code] = [
                        {"date": str(r["date"])[:10], "value": float(r["value"])}
                        for _, r in df.iterrows()
                    ]
                else:
                    indicators[code] = []
            except Exception:
                indicators[code] = []
    except ImportError:
        for code in ["CN_CPI_YOY", "CN_PPI_YOY", "CN_PMI", "CN_LPR_1Y",
                      "US_CPI_YOY", "US_FED_FUNDS", "US_UNEMPLOYMENT", "US_10Y_YIELD"]:
            indicators[code] = []

    return {
        "indicators": indicators,
        "generated_at": datetime.now().isoformat(),
    }


def build_macro_panel_html() -> str:
    """生成宏观面板 HTML"""
    data = build_macro_data_api()
    indicators = data["indicators"]

    chart_divs = ""
    color_map = {
        "CN_CPI_YOY": "#3b82f6", "CN_PPI_YOY": "#8b5cf6",
        "CN_PMI": "#10b981", "CN_LPR_1Y": "#f59e0b",
        "US_CPI_YOY": "#ef4444", "US_FED_FUNDS": "#06b6d4",
        "US_UNEMPLOYMENT": "#ec4899", "US_10Y_YIELD": "#f59e0b",
    }

    for i, (code, history) in enumerate(indicators.items()):
        if not history:
            continue
        dates = [h["date"] for h in history]
        values = [h["value"] for h in history]
        color = color_map.get(code, "#3b82f6")

        fig = {
            "data": [{
                "x": dates, "y": values,
                "type": "scatter", "mode": "lines",
                "line": {"color": color, "width": 2},
            }],
            "layout": {
                "title": {"text": code, "font": {"color": "#f1f5f9"}},
                "xaxis": {"gridcolor": "#1e293b", "color": "#94a3b8"},
                "yaxis": {"gridcolor": "#1e293b", "color": "#94a3b8"},
                "paper_bgcolor": "#0b0f1a", "plot_bgcolor": "#0b0f1a",
                "margin": {"l": 50, "r": 10, "t": 40, "b": 30},
            },
        }
        fig_json = json.dumps(fig)

        chart_divs += f"""
        <div style="background:#111827;padding:12px;border-radius:8px;margin-bottom:16px;">
            <div id="macro_{i}" style="width:100%;height:260px;"></div>
            <script>
                Plotly.newPlot('macro_{i}', {fig_json}['data'], {fig_json}['layout'],
                    {{responsive: true, displayModeBar: false}});
            </script>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>宏观数据面板</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
    body {{ background: #060912; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;
           margin: 0; padding: 20px; }}
    h1 {{ color: #3b82f6; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
</style>
</head><body>
<h1>Macro Dashboard</h1>
<div class="grid">{chart_divs}</div>
<p style="color:#475569;margin-top:20px;">Generated: {data['generated_at']}</p>
</body></html>"""
