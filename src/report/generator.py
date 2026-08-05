"""
每日简报生成器 (v6.0)
生成 HTML/文本 格式的每日量化简报
"""

import os, json
from datetime import datetime
from typing import Dict, List


def generate_daily_report(output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", os.path.expanduser("~/lxl_quantaxis_data"))) + "/reports"
    """
    生成每日简报 (HTML格式, 浏览器可打印为PDF)
    返回: 文件路径
    """
    from src.models.trade import TradeRepository
    from daily_runner import quick_diagnosis, DEFAULT_WATCHLIST
    from src.backtest.data_feed import get_data, get_data_summary, download_watchlist
    from src.data.stock_db import ensure_stock_db

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    now_str = today.strftime("%Y-%m-%d %H:%M")

    repo = TradeRepository()
    db = ensure_stock_db()

    # 1. 持仓分析
    positions = repo.find_open_positions()
    pos_data = []
    total_market_value = 0
    total_pnl = 0
    for p in positions:
        try:
            d = get_data(p.symbol, "A股", start_date="2024-01-01")
            if d is not None and len(d) > 0:
                px = float(d["close"].iloc[-1])
                pnl = (px - p.price) * p.quantity
                pnl_pct = (px / p.price - 1) * 100
                total_market_value += px * p.quantity
                total_pnl += pnl
                pos_data.append({
                    "symbol": p.symbol, "name": p.name,
                    "cost": p.price, "price": round(px, 2),
                    "qty": p.quantity, "pnl": round(pnl, 0),
                    "pnl_pct": round(pnl_pct, 1),
                })
        except:
            pass

    # 2. 每日扫描
    scan_results = []
    for item in DEFAULT_WATCHLIST[:10]:
        try:
            r = quick_diagnosis(item["symbol"], item.get("market", "A股"),
                              item.get("name", item["symbol"]))
            if not r.get("error"):
                scan_results.append(r)
        except:
            pass
    scan_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 3. 市场概况
    market_summary = _get_market_summary()

    # 4. 生成 HTML
    html = _build_html(today_str, now_str, pos_data, total_market_value, total_pnl,
                       scan_results, market_summary)

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"daily_report_{today_str}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    # 同时生成文本版
    txt_path = os.path.join(output_dir, f"daily_report_{today_str}.txt")
    txt = _build_text(today_str, now_str, pos_data, total_market_value, total_pnl,
                      scan_results, market_summary)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)

    print(f"\n  简报已生成:")
    print(f"  HTML: {path}")
    print(f"  TXT:  {txt_path}")
    return path


def _get_market_summary() -> dict:
    """获取市场概况"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and len(df) > 0:
            up = (df["涨跌幅"] > 0).sum()
            down = (df["涨跌幅"] < 0).sum()
            total = len(df)
            return {"up": int(up), "down": int(down), "total": total,
                    "ratio": f"{up}:{down}", "up_pct": round(up/total*100, 1)}
    except:
        pass
    return {"up": 0, "down": 0, "total": 0, "ratio": "N/A", "up_pct": 0}


def _build_html(date: str, now: str, positions: list, total_val: float, total_pnl: float,
                scan: list, market: dict) -> str:
    """构建 HTML 简报"""
    pos_rows = ""
    for p in positions:
        cls = "up" if p["pnl"] >= 0 else "down"
        pos_rows += f"""<tr>
<td>{p['symbol']}</td><td>{p['name']}</td><td>{p['cost']:.2f}</td><td>{p['price']:.2f}</td>
<td>{p['qty']}</td><td class="{cls}">{p['pnl_pct']:+.1f}%</td><td class="{cls}">{p['pnl']:+,.0f}</td>
</tr>"""

    scan_rows = ""
    for i, s in enumerate(scan[:8], 1):
        cls = "buy" if s["score"] >= 60 else ("wait" if s["score"] >= 40 else "sell")
        action = "买入" if s["score"] >= 60 else ("观望" if s["score"] >= 40 else "回避")
        scan_rows += f"""<tr>
<td>{i}</td><td>{s['symbol']}</td><td>{s.get('name','')}</td><td>{s['price']:.2f}</td>
<td class="{cls}">{s['score']}/100</td><td>{action}</td>
</tr>"""

    up_pct = market.get("up_pct", 0)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>QuantAxis 每日简报 {date}</title>
<style>
body{{font-family:'Microsoft YaHei',sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#1a1a2e;background:#f8f9fa}}
.header{{text-align:center;padding:24px 0;border-bottom:3px solid #3b82f6;margin-bottom:24px}}
.header h1{{margin:0;color:#0B1F3A;font-size:24px}}
.header p{{color:#6b7280;margin:4px 0 0}}
.card{{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card h2{{margin:0 0 12px;font-size:16px;color:#3b82f6;border-left:3px solid #3b82f6;padding-left:10px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#f1f5f9;padding:8px 12px;text-align:left;font-weight:600;color:#475569}}
td{{padding:7px 12px;border-bottom:1px solid #f1f5f9}}
.up{{color:#10b981;font-weight:600}}.down{{color:#ef4444;font-weight:600}}
.buy{{color:#10b981;font-weight:700}}.wait{{color:#f59e0b}}.sell{{color:#ef4444}}
.kpis{{display:flex;gap:12px;margin-bottom:16px}}
.kpi{{flex:1;background:#fff;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.kpi .val{{font-size:22px;font-weight:700;margin:4px 0}}
.kpi .lbl{{font-size:11px;color:#6b7280;text-transform:uppercase}}
.footer{{text-align:center;color:#9ca3af;font-size:11px;margin-top:24px;padding-top:16px;border-top:1px solid #e5e7eb}}
</style></head><body>
<div class="header"><h1>LXL·QuantAxis 每日量化简报</h1><p>{date} | {now}</p></div>

<div class="kpis">
<div class="kpi"><div class="lbl">持仓市值</div><div class="val">{total_val:,.0f}</div></div>
<div class="kpi"><div class="lbl">持仓盈亏</div><div class="val" style="color:{ '#10b981' if total_pnl >= 0 else '#ef4444' }">{total_pnl:+,.0f}</div></div>
<div class="kpi"><div class="lbl">上涨家数</div><div class="val" style="color:#10b981">{up_pct}%</div></div>
<div class="kpi"><div class="lbl">信号股票</div><div class="val" style="color:#3b82f6">{len(scan)}</div></div>
</div>

<div class="card"><h2>📦 持仓概览</h2>
{"<p style='color:#9ca3af'>当前无持仓</p>" if not positions else f"<table><thead><tr><th>代码</th><th>名称</th><th>成本</th><th>现价</th><th>数量</th><th>盈亏%</th><th>盈亏</th></tr></thead><tbody>{pos_rows}</tbody></table>"}
</div>

<div class="card"><h2>🔥 今日信号 (因子评分排名)</h2>
<table><thead><tr><th>#</th><th>代码</th><th>名称</th><th>价格</th><th>评分</th><th>建议</th></tr></thead><tbody>{scan_rows}</tbody></table>
</div>

<div class="card"><h2>📊 市场概况</h2>
<p>上涨: <b style="color:#10b981">{market.get('up',0)}</b> | 下跌: <b style="color:#ef4444">{market.get('down',0)}</b> | 总计: {market.get('total',0)} | 涨跌比: {market.get('ratio','N/A')}</p>
</div>

<div class="footer">LXL·QuantAxis v6.0 自动生成 | 仅供参考,不构成投资建议</div>
</body></html>"""


def _build_text(date: str, now: str, positions: list, total_val: float, total_pnl: float,
                scan: list, market: dict) -> str:
    """文本版简报"""
    lines = []
    lines.append("=" * 56)
    lines.append(f"  LXL·QuantAxis 每日量化简报")
    lines.append(f"  {date}  {now}")
    lines.append("=" * 56)
    lines.append(f"  持仓市值: {total_val:,.0f}  盈亏: {total_pnl:+,.0f}")
    lines.append(f"  市场: 涨{market.get('up',0)} / 跌{market.get('down',0)}")
    lines.append("")
    lines.append("── 持仓 ──")
    if positions:
        for p in positions:
            lines.append(f"  {p['symbol']} {p['name']}: {p['cost']:.2f}→{p['price']:.2f} {p['pnl_pct']:+.1f}%")
    else:
        lines.append("  无持仓")
    lines.append("")
    lines.append("── 今日信号 ──")
    for i, s in enumerate(scan[:8], 1):
        action = "买入" if s["score"] >= 60 else ("观望" if s["score"] >= 40 else "回避")
        lines.append(f"  {i}. {s['symbol']} {s.get('name','')}: {s['price']:.2f} 评分{s['score']}/100 {action}")
    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)
