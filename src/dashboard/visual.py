"""
可视化仪表盘 v2.0 — 嵌入 Plotly 交互图表

三个面板:
  1. 管理面板   — KPI + 策略清单 + 最近交易
  2. 绩效仪表盘 — 资金曲线TOP5 + 夏普收益矩阵 + 月度热力
  3. 数据健康   — 缓存一览 + 覆盖率
"""

import os, sys, json, webbrowser
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from plotly.utils import PlotlyJSONEncoder

from src.config import config
from src.backtest.batch_runner import ResultDB
from src.backtest.data_feed import get_data_summary, CACHE_DIR, get_data, get_data_summary
from src.models.trade import TradeRepository

DB_PATH = os.path.join(config.data_dir, "trades.db")
RESULTS_DB = os.path.join(config.data_dir, "backtest_results.db")
repo = TradeRepository(DB_PATH)
result_db = ResultDB(RESULTS_DB)

# ============================================================
# HTML 组件
# ============================================================

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  background:linear-gradient(135deg,#0b1120 0%,#111827 100%);color:#e2e8f0;padding:24px;min-height:100vh}
h1{font-size:28px;font-weight:700;letter-spacing:-0.5px;margin-bottom:4px;
  background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
h2{font-size:17px;margin:28px 0 14px;padding-bottom:10px;border-bottom:1px solid #1e293b;color:#cbd5e1;letter-spacing:0.3px}
.sub{color:#64748b;font-size:13px;margin-bottom:24px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:28px}
.kpi{background:linear-gradient(135deg,#1e293b,#1a2332);border:1px solid #1e293b;border-radius:14px;padding:22px 18px;
  text-align:center;transition:transform .15s,box-shadow .15s;cursor:default}
.kpi:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,0.3)}
.kpi .icon{font-size:24px;margin-bottom:4px}
.kpi .label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px}
.kpi .val{font-size:30px;font-weight:800}
.kpi .sub{font-size:11px;color:#64748b;margin-top:2px}
.green{color:#22c55e}.red{color:#ef4444}.yellow{color:#eab308}.blue{color:#3b82f6}.purple{color:#a78bfa}
.card{background:#111827;border:1px solid #1e293b;border-radius:14px;padding:22px;margin-bottom:18px}
.card h3{font-size:15px;margin-bottom:14px;color:#e2e8f0;font-weight:600}
.chart-wrap{background:#0f172a;border-radius:10px;padding:8px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:rgba(30,41,59,0.8);padding:10px 14px;text-align:left;font-weight:600;color:#94a3b8;font-size:11px;
  text-transform:uppercase;letter-spacing:0.5px}
td{padding:9px 14px;border-bottom:1px solid #1e293b}
tr:hover td{background:rgba(59,130,246,0.04)}
.tag{padding:3px 8px;border-radius:5px;font-size:10px;font-weight:700;letter-spacing:0.3px}
.tag-ok{background:#14532d;color:#86efac}.tag-warn{background:#78350f;color:#fcd34d}
.tag-err{background:#7f1d1d;color:#fca5a5}.tag-info{background:#1e3a5f;color:#93c5fd}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.footer{text-align:center;color:#334155;font-size:11px;margin-top:48px;padding:20px;border-top:1px solid #1e293b}
"""

JS_LIBS = '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

def _page(title, content, auto_refresh=0):
    refresh = f'<meta http-equiv="refresh" content="{auto_refresh}">' if auto_refresh else ''
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>{refresh}
<style>{CSS}</style>{JS_LIBS}</head><body>{content}<div class="footer">
量化系统 v{config.version} · 数据目录: {config.data_dir} · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div></body></html>"""

def _chart_div(fig, height=400):
    """将 Plotly figure 转为 HTML div"""
    fig.update_layout(
        height=height, margin=dict(l=60, r=20, t=30, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8', size=11),
        xaxis=dict(gridcolor='#1e293b', zeroline=False),
        yaxis=dict(gridcolor='#1e293b', zeroline=False),
    )
    js = json.dumps(fig, cls=PlotlyJSONEncoder)
    chart_id = f"chart_{id(fig)}"
    return f'<div class="chart-wrap"><div id="{chart_id}"></div></div>\n<script>Plotly.newPlot("{chart_id}", {js}, {{responsive:true}});</script>'


# ============================================================
# 1. 管理面板
# ============================================================

def build_system_overview(auto_refresh=0):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # KPI 数据
    total_trades = repo.count()
    positions = len(repo.find_open_positions())
    pnl_list = repo.get_all_pnl()
    total_pnl = sum(p["net_pnl"] for p in pnl_list) if pnl_list else 0
    wins = len([p for p in pnl_list if p["net_pnl"] > 0]) if pnl_list else 0
    win_rate = wins / max(len(pnl_list), 1) * 100

    cache_df = get_data_summary()
    cache_count = len(cache_df)
    cache_rows = int(cache_df["行数"].sum()) if not cache_df.empty else 0

    summary = result_db.summary()
    result_count = summary.get("总回测数", 0)

    # === 盈亏趋势图 ===
    pnl_trend_html = ""
    if pnl_list:
        monthly = {}
        for p in pnl_list:
            m = p.get("sell_date", "")[:7]
            if m:
                monthly[m] = monthly.get(m, 0) + p["net_pnl"]
        if monthly:
            months = sorted(monthly.keys())
            cumsum = np.cumsum([monthly[m] for m in months])
            fig = go.Figure()
            fig.add_trace(go.Bar(x=months, y=[monthly[m] for m in months],
                name="月盈亏", marker=dict(color=["#22c55e" if v>=0 else "#ef4444" for v in [monthly[m] for m in months]])))
            fig.add_trace(go.Scatter(x=months, y=cumsum, name="累计盈亏",
                line=dict(color="#3b82f6", width=2.5), yaxis="y2"))
            fig.update_layout(yaxis=dict(title="月盈亏 ¥"), yaxis2=dict(title="累计 ¥", overlaying="y", side="right"))
            pnl_trend_html = _chart_div(fig, 320)

    # === 策略状态表 ===
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES
    strat_rows = ""
    for key, info in {**STRATEGIES, **PRESET_STRATEGIES}.items():
        results = result_db.query(strategy=key, limit=500)
        n = len(results)
        avg_s = np.mean([r["sharpe"] for r in results]) if results else 0
        tag_cls = "tag-info" if key in STRATEGIES else "tag-warn"
        tag_text = "经典" if key in STRATEGIES else "独有"
        sc = "green" if avg_s > 0.3 else ("yellow" if avg_s > -0.3 else "red")
        strat_rows += f'<tr><td><span class="tag {tag_cls}">{tag_text}</span> {info["name"]}</td><td>{info["description"]}</td><td>{n}</td><td class="{sc}">{avg_s:+.2f}</td></tr>'

    # === 最近交易 ===
    recent = repo.find_all(limit=8)
    trade_rows = ""
    for t in recent:
        pnl_str = '<span style="color:#64748b">-</span>'
        if t.trade_type == "买入" and t.paired_trade_id:
            pnl = repo.calc_pnl(t.id)
            if pnl:
                c = "green" if pnl["net_pnl"] >= 0 else "red"
                pnl_str = f'<span class="{c}">¥{pnl["net_pnl"]:+,.2f}</span>'
        trade_rows += f'<tr><td>{t.trade_date}</td><td>{t.market} {t.symbol}</td><td>{t.name}</td><td>{t.trade_type}</td><td>¥{t.price:.2f}×{t.quantity}</td><td>{pnl_str}</td></tr>'

    content = f"""
<h1>📈 量化管理系统</h1>
<p class="sub">v{config.version} · 数据: {config.data_dir} · 刷新: {now}</p>

<div class="kpis">
  <div class="kpi"><div class="icon">📒</div><div class="label">交易记录</div><div class="val blue">{total_trades}</div><div class="sub">笔</div></div>
  <div class="kpi"><div class="icon">📦</div><div class="label">当前持仓</div><div class="val yellow">{positions}</div><div class="sub">只</div></div>
  <div class="kpi"><div class="icon">💰</div><div class="label">总盈亏</div><div class="val {'green' if total_pnl>=0 else 'red'}">¥{total_pnl:+,.0f}</div><div class="sub">胜率 {win_rate:.0f}%</div></div>
  <div class="kpi"><div class="icon">💾</div><div class="label">数据缓存</div><div class="val blue">{cache_count}</div><div class="sub">{cache_rows:,} 行</div></div>
  <div class="kpi"><div class="icon">🔬</div><div class="label">回测记录</div><div class="val purple">{result_count}</div><div class="sub">条</div></div>
</div>

<div class="grid2">
  <div class="card"><h3>📊 月度盈亏趋势</h3>{pnl_trend_html or '<p style="color:#64748b;text-align:center;padding:40px">暂无已完成交易</p>'}</div>
  <div class="card"><h3>📋 最近交易</h3><table><thead><tr><th>日期</th><th>代码</th><th>名称</th><th>类型</th><th>成交</th><th>盈亏</th></tr></thead><tbody>{trade_rows if trade_rows else '<tr><td colspan="6" style="color:#64748b;text-align:center;padding:20px">暂无记录</td></tr>'}</tbody></table></div>
</div>

<h2>📋 策略清单 & 表现</h2>
<div class="card"><table>
<thead><tr><th>策略</th><th>逻辑</th><th>回测次数</th><th>平均夏普</th></tr></thead>
<tbody>{strat_rows}</tbody></table></div>
"""
    return _page("量化系统 · 管理面板", content, auto_refresh)


# ============================================================
# 2. 绩效仪表盘
# ============================================================

def build_performance_dashboard():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_results = result_db.query(limit=5000)
    if not all_results:
        return _page("绩效仪表盘", '<h1>📊 绩效仪表盘</h1><div class="card"><p style="color:#64748b;text-align:center;padding:60px">暂无回测数据<br><br>请先运行 菜单3→批量回测</p></div>')

    df = pd.DataFrame(all_results)

    # === TOP 10 ===
    top10 = df.nlargest(10, "sharpe")
    top_rows = ""
    for _, r in top10.iterrows():
        sc = "green" if r["sharpe"] > 0.3 else ("yellow" if r["sharpe"] > -0.3 else "red")
        rc = "green" if r["total_return"] > 0 else "red"
        top_rows += f'<tr><td>{r["symbol"]}</td><td><strong>{r["strategy"]}</strong></td><td class="{rc}">{r["total_return"]:+.1f}%</td><td class="{sc}">{r["sharpe"]:.2f}</td><td class="red">{r["max_drawdown"]:.1f}%</td><td>{r["win_rate"]:.1f}%</td><td>{r["trade_count"]:.0f}</td></tr>'

    # === 夏普矩阵热力图 ===
    pivot = df.pivot_table(values="sharpe", index="strategy", columns="symbol", aggfunc="mean")
    matrix_html = ""
    if not pivot.empty:
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale=[[0,"#ef4444"],[0.4,"#1e293b"],[0.55,"#1e293b"],[0.7,"#22c55e"],[1,"#16a34a"]],
            zmid=0, text=[[f"{v:.2f}" if not np.isnan(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}", textfont=dict(size=12, color="#e2e8f0"),
            colorbar=dict(title="夏普", tickfont=dict(color="#94a3b8")),
        ))
        matrix_html = _chart_div(fig, 350)

    # === 收益率散点图 (夏普 vs 收益) ===
    scatter_html = ""
    if len(df) > 1:
        fig = px.scatter(df, x="total_return", y="sharpe", color="strategy",
            size="trade_count", hover_data=["symbol"],
            labels={"total_return":"总收益率 %", "sharpe":"夏普比率"},
            color_discrete_sequence=px.colors.qualitative.Bold)
        fig.add_hline(y=0, line_dash="dash", line_color="#334155")
        fig.add_vline(x=0, line_dash="dash", line_color="#334155")
        scatter_html = _chart_div(fig, 380)

    # === 按策略统计 ===
    strat_stats = df.groupby("strategy").agg(
        avg_sharpe=("sharpe","mean"), avg_return=("total_return","mean"),
        count=("sharpe","count"), best_return=("total_return","max"),
        avg_winrate=("win_rate","mean")
    ).round(2).sort_values("avg_sharpe", ascending=False)
    stats_rows = ""
    for name, r in strat_stats.iterrows():
        sc = "green" if r["avg_sharpe"] > 0.3 else ("yellow" if r["avg_sharpe"] > -0.3 else "red")
        stats_rows += f'<tr><td><strong>{name}</strong></td><td>{r["count"]:.0f}</td><td class="{sc}">{r["avg_sharpe"]:+.2f}</td><td class="{"green" if r["avg_return"]>0 else "red"}">{r["avg_return"]:+.1f}%</td><td>{r["avg_winrate"]:.1f}%</td><td class="green">{r["best_return"]:+.1f}%</td></tr>'

    content = f"""
<h1>📊 策略绩效仪表盘</h1>
<p class="sub">刷新: {now} · 共 {len(all_results)} 条回测记录</p>

<div class="kpis">
  <div class="kpi"><div class="icon">🏆</div><div class="label">最佳夏普</div><div class="val green">{df["sharpe"].max():.2f}</div><div class="sub">{df.loc[df["sharpe"].idxmax(), "strategy"]} @ {df.loc[df["sharpe"].idxmax(), "symbol"]}</div></div>
  <div class="kpi"><div class="icon">📈</div><div class="label">最佳收益</div><div class="val green">{df["total_return"].max():+.1f}%</div><div class="sub">{df.loc[df["total_return"].idxmax(), "strategy"]} @ {df.loc[df["total_return"].idxmax(), "symbol"]}</div></div>
  <div class="kpi"><div class="icon">📉</div><div class="label">平均夏普</div><div class="val yellow">{df["sharpe"].mean():.2f}</div><div class="sub">全部策略均值</div></div>
  <div class="kpi"><div class="icon">🎯</div><div class="label">平均胜率</div><div class="val blue">{df["win_rate"].mean():.1f}%</div><div class="sub">{len(df["strategy"].unique())} 策略 × {len(df["symbol"].unique())} 标的</div></div>
</div>

<div class="grid2">
  <div class="card"><h3>🏆 TOP 10 排名</h3><table><thead><tr><th>标的</th><th>策略</th><th>收益</th><th>夏普</th><th>回撤</th><th>胜率</th><th>交易</th></tr></thead><tbody>{top_rows}</tbody></table></div>
  <div class="card"><h3>📈 策略综合对比</h3><table><thead><tr><th>策略</th><th>次数</th><th>Avg夏普</th><th>Avg收益</th><th>胜率</th><th>最佳</th></tr></thead><tbody>{stats_rows}</tbody></table></div>
</div>

<h2>🔥 夏普比率矩阵</h2>
<div class="card">{matrix_html}</div>

<h2>📈 收益 vs 夏普</h2>
<div class="card">{scatter_html}</div>
"""
    return _page("绩效仪表盘", content)


# ============================================================
# 3. 数据健康面板
# ============================================================

def build_data_health():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cache_df = get_data_summary()

    rows = ""
    total_rows = 0
    if not cache_df.empty:
        total_rows = int(cache_df["行数"].sum())
        for _, r in cache_df.iterrows():
            rows += f'<tr><td>{r["文件"]}</td><td>{r["行数"]:.0f}</td><td>{r["起始日期"]}</td><td>{r["结束日期"]}</td><td>{r["大小(KB)"]:.1f}</td></tr>'

    # 覆盖时间轴
    timeline_html = ""
    if not cache_df.empty:
        fig = go.Figure()
        for _, r in cache_df.iterrows():
            fig.add_trace(go.Bar(
                x=[r["文件"]], y=[r["行数"]],
                name=r["文件"], text=f'{r["行数"]:.0f}行',
                marker=dict(color="#3b82f6", opacity=0.7)
            ))
        fig.update_layout(showlegend=False, height=300)
        timeline_html = _chart_div(fig, 300)

    content = f"""
<h1>📥 数据健康面板</h1>
<p class="sub">刷新: {now} · 缓存: {CACHE_DIR}</p>

<div class="kpis">
  <div class="kpi"><div class="icon">📁</div><div class="label">缓存文件</div><div class="val blue">{len(cache_df)}</div><div class="sub">个</div></div>
  <div class="kpi"><div class="icon">📊</div><div class="label">数据总量</div><div class="val purple">{total_rows:,}</div><div class="sub">行</div></div>
  <div class="kpi"><div class="icon">📅</div><div class="label">最早数据</div><div class="val blue">{cache_df['起始日期'].min() if not cache_df.empty else 'N/A'}</div><div class="sub">起始</div></div>
  <div class="kpi"><div class="icon">🕐</div><div class="label">最新数据</div><div class="val green">{cache_df['结束日期'].max() if not cache_df.empty else 'N/A'}</div><div class="sub">结束</div></div>
</div>

<h2>📊 缓存文件一览</h2>
<div class="card"><table>
<thead><tr><th>文件</th><th>行数</th><th>起始</th><th>结束</th><th>大小</th></tr></thead>
<tbody>{rows if rows else '<tr><td colspan="5" style="color:#64748b;text-align:center;padding:30px">缓存为空，请先下载数据 (菜单7→1)</td></tr>'}</tbody>
</table></div>

<h2>📈 数据量分布</h2>
<div class="card">{timeline_html if timeline_html else '<p style="color:#64748b;text-align:center;padding:40px">无数据</p>'}</div>
"""
    return _page("数据健康", content)


# ============================================================
# 4. 综合报告（批量回测后自动生成）
# ============================================================

def build_batch_report(run_df: pd.DataFrame, run_time: float = 0):
    """批量回测后自动生成综合报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_symbols = run_df["symbol"].nunique() if "symbol" in run_df.columns else 0
    n_strategies = run_df["strategy"].nunique() if "strategy" in run_df.columns else 0
    n_total = len(run_df)

    # TOP 表格
    top10 = run_df.head(10) if not run_df.empty else pd.DataFrame()
    top_rows = ""
    for _, r in top10.iterrows():
        sc = "green" if r.get("夏普比率", 0) > 0.3 else "red"
        top_rows += f'<tr><td>{r.get("symbol","")}</td><td><strong>{r.get("strategy","")}</strong></td><td class="{"green" if r.get("总收益率","0%")>"0" else "red"}">{r.get("总收益率","")}</td><td class="{sc}">{r.get("夏普比率",0):.2f}</td><td>{r.get("胜率","")}</td><td>{r.get("交易次数",0)}</td></tr>'

    content = f"""
<h1>📊 批量回测报告</h1>
<p class="sub">生成: {now} · 耗时: {run_time:.1f}秒</p>

<div class="kpis">
  <div class="kpi"><div class="icon">🎯</div><div class="label">测试标的</div><div class="val blue">{n_symbols}</div><div class="sub">只</div></div>
  <div class="kpi"><div class="icon">🧪</div><div class="label">测试策略</div><div class="val purple">{n_strategies}</div><div class="sub">个</div></div>
  <div class="kpi"><div class="icon">🔬</div><div class="label">总回测数</div><div class="val blue">{n_total}</div><div class="sub">次</div></div>
  <div class="kpi"><div class="icon">⏱️</div><div class="label">总耗时</div><div class="val yellow">{run_time:.1f}s</div><div class="sub">秒</div></div>
</div>

<h2>🏆 回测排名 TOP 10</h2>
<div class="card"><table>
<thead><tr><th>标的</th><th>策略</th><th>收益</th><th>夏普</th><th>胜率</th><th>交易</th></tr></thead>
<tbody>{top_rows}</tbody></table></div>
"""
    return _page("批量回测报告", content)


# ============================================================
# 生成 + 打开
# ============================================================

DASHBOARD_DIR = os.path.join(config.data_dir, "dashboards")


def generate_all():
    """生成全部仪表盘"""
    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    files = {}

    panels = {
        "overview": ("管理面板", build_system_overview),
        "performance": ("绩效仪表盘", build_performance_dashboard),
        "data_health": ("数据健康", build_data_health),
    }

    for name, (title, builder) in panels.items():
        path = os.path.join(DASHBOARD_DIR, f"{name}.html")
        try:
            html = builder()
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            files[name] = (title, path)
        except Exception as e:
            print(f"  ⚠️ {title} 生成失败: {e}")

    return files


def open_dashboard(name: str = "overview"):
    """打开指定仪表盘"""
    files = generate_all()
    if name in files:
        _, path = files[name]
        url = f"file:///{path.replace(chr(92), '/')}"
        webbrowser.open(url)
        print(f"  ✅ 已打开: {files[name][0]}")
        return files
    # fallback
    for n, (t, p) in files.items():
        webbrowser.open(f"file:///{p.replace(chr(92), '/')}")
        print(f"  ✅ 已打开: {t}")
        break
    return files


def open_all():
    """一键打开所有仪表盘"""
    files = generate_all()
    for name, (title, path) in files.items():
        webbrowser.open(f"file:///{path.replace(chr(92), '/')}")
        print(f"  ✅ {title}")
    return files
