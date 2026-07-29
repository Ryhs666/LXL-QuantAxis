"""
指数估值分析 — PE/PB 历史分位数 + 估值带

核心功能:
  - 获取指数 PE/PB 历史序列
  - 计算当前估值分位数（处于历史什么位置）
  - 判断估值区间（低估/正常/高估）
  - 生成估值仪表盘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict

from src.config import config

# ============================================================
# 指数 ETF 映射表
# ============================================================

INDEX_ETF_MAP = {
    # 指数代码: (名称, ETF代码, ETF名称, 市场)
    "000300": ("沪深300", "510300", "沪深300ETF", "A股"),
    "000016": ("上证50", "510050", "上证50ETF", "A股"),
    "000905": ("中证500", "510500", "中证500ETF", "A股"),
    "000852": ("中证1000", "512100", "中证1000ETF", "A股"),
    "399006": ("创业板指", "159915", "创业板ETF", "A股"),
    "000688": ("科创50", "588000", "科创50ETF", "A股"),
    "399001": ("深证成指", "159903", "深成ETF", "A股"),
    "000903": ("中证100", "512910", "中证100ETF", "A股"),
    "399330": ("深证100", "159901", "深100ETF", "A股"),
    "000922": ("中证红利", "515080", "中证红利ETF", "A股"),
    "H00300": ("恒生指数", "02800", "盈富基金", "港股"),
    "HSTECH": ("恒生科技", "03033", "恒生科技ETF", "港股"),
}

FAVORITE_INDICES = ["000300", "000016", "000905", "399006", "000688", "000922"]


def list_indices():
    """列出所有支持的指数"""
    print("\n  📊 指数 ETF 列表:")
    print(f"  {'代码':<10} {'指数名称':<10} {'ETF代码':<10} {'ETF名称':<15}")
    print("  " + "-" * 48)
    for code, (name, etf, etf_name, market) in INDEX_ETF_MAP.items():
        print(f"  {code:<10} {name:<10} {etf:<10} {etf_name:<15} {market}")


# ============================================================
# 估值数据获取
# ============================================================

def get_index_valuation(index_code: str, use_cache: bool = True) -> pd.DataFrame:
    """
    获取指数 PE/PB 历史序列

    返回 DataFrame:
      date, pe, pb, close
    """
    cache_path = os.path.join(config.data_dir, "cache", f"valuation_{index_code}.csv")

    if use_cache and os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["date"])
        latest = df["date"].max()
        if isinstance(latest, pd.Timestamp):
            latest = latest.date()
        else:
            latest = pd.Timestamp(latest).date()
        if (datetime.now().date() - latest).days <= 1:
            return df

    try:
        import akshare as ak

        # 尝试获取指数估值数据
        if index_code == "000300":
            df = ak.index_value_hist_funddb(symbol="000300", indicator="市盈率")
            if df is not None and not df.empty:
                df = df.rename(columns={"日期": "date", "市盈率": "pe"})
                # PB 用另一接口
                try:
                    pb_df = ak.index_value_hist_funddb(symbol="000300", indicator="市净率")
                    pb_df = pb_df.rename(columns={"日期": "date", "市净率": "pb"})
                    df = df.merge(pb_df, on="date")
                except Exception:
                    df["pb"] = np.nan
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                df.to_csv(cache_path, index=False)
                return df

        # 回退：用指数价格数据 + 平均估值估算
        from src.backtest.data_feed import get_index_data
        price_df = get_index_data(index_code, start_date="2015-01-01")

        # 尝试从 akshare 获取估值
        try:
            val_df = ak.index_value_name_funddb()
            if val_df is not None and not val_df.empty:
                # 过滤该指数
                name = INDEX_ETF_MAP.get(index_code, ("",))[0]
                if name:
                    match = val_df[val_df["名称"].str.contains(name.replace("指", ""))]
                    if not match.empty:
                        print(f"    估值快照: {match.iloc[0].to_dict()}")
        except Exception:
            pass

        # 如果获取不到估值数据，返回价格数据 + 占位列
        if price_df is not None and not price_df.empty:
            df = price_df[["date", "close"]].copy()
            df["pe"] = np.nan
            df["pb"] = np.nan
            df.to_csv(cache_path, index=False)
            return df

        return pd.DataFrame()

    except Exception as e:
        print(f"    ⚠️ 估值数据获取失败 ({index_code}): {e}")
        return pd.DataFrame()


def get_valuation_snapshot() -> pd.DataFrame:
    """
    获取所有主流指数的当前估值快照

    返回: DataFrame (指数, 名称, 当前PE, PE分位, PE评级, 当前PB, PB分位, PB评级)
    """
    rows = []
    for code in FAVORITE_INDICES:
        name, etf, etf_name, _ = INDEX_ETF_MAP.get(code, (code, "", "", ""))
        try:
            df = get_index_valuation(code)
            if df.empty:
                rows.append({"指数": code, "名称": name, "状态": "数据缺失"})
                continue

            pe_col = "pe" if "pe" in df.columns else None
            pb_col = "pb" if "pb" in df.columns else None

            latest = df.iloc[-1]

            row = {"指数": code, "名称": name, "ETF": etf}

            if pe_col and not pd.isna(latest.get("pe")):
                pe_now = latest["pe"]
                pe_hist = df["pe"].dropna()
                pe_pct = (pe_hist < pe_now).sum() / len(pe_hist) * 100
                pe_zone = _valuation_zone(pe_pct)
                row["PE"] = f"{pe_now:.1f}"
                row["PE分位"] = f"{pe_pct:.0f}%"
                row["PE评级"] = pe_zone
            else:
                row["PE"] = "N/A"
                row["PE分位"] = "N/A"
                row["PE评级"] = "-"

            if pb_col and not pd.isna(latest.get("pb")):
                pb_now = latest["pb"]
                pb_hist = df["pb"].dropna()
                pb_pct = (pb_hist < pb_now).sum() / len(pb_hist) * 100
                pb_zone = _valuation_zone(pb_pct)
                row["PB"] = f"{pb_now:.1f}"
                row["PB分位"] = f"{pb_pct:.0f}%"
                row["PB评级"] = pb_zone

            rows.append(row)

        except Exception as e:
            rows.append({"指数": code, "名称": name, "状态": f"失败: {e}"})

    return pd.DataFrame(rows)


def _valuation_zone(percentile: float) -> str:
    """估值区间判断"""
    if percentile <= 20:
        return "🟢 低估"
    elif percentile <= 40:
        return "🟡 偏低"
    elif percentile <= 60:
        return "⚪ 合理"
    elif percentile <= 80:
        return "🟠 偏高"
    else:
        return "🔴 高估"


# ============================================================
# 估值仪表盘
# ============================================================

def build_valuation_dashboard() -> str:
    """生成估值仪表盘 HTML"""
    snapshot = get_valuation_snapshot()

    rows = ""
    if not snapshot.empty:
        for _, r in snapshot.iterrows():
            zone = r.get("PE评级", "")
            color = "#22c55e" if "低估" in str(zone) else ("#ef4444" if "高估" in str(zone) else ("#eab308" if "偏高" in str(zone) or "偏低" in str(zone) else "#94a3b8"))
            rows += f"""<tr>
            <td>{r['指数']}</td><td><strong>{r['名称']}</strong></td><td>{r.get('ETF','')}</td>
            <td>{r.get('PE','N/A')}</td><td>{r.get('PE分位','N/A')}</td><td style="color:{color};font-weight:600">{zone}</td>
            <td>{r.get('PB分位','N/A')}</td></tr>"""

    css = """
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(135deg,#0b1120,#111827);color:#e2e8f0;padding:24px}
    h1{font-size:26px;margin-bottom:4px;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
    .sub{color:#64748b;font-size:13px;margin-bottom:24px}
    table{width:100%;border-collapse:collapse;font-size:14px}
    th{background:#1e293b;padding:12px 14px;text-align:left;font-weight:600;color:#94a3b8;font-size:11px;text-transform:uppercase}
    td{padding:10px 14px;border-bottom:1px solid #1e293b}
    tr:hover td{background:rgba(59,130,246,0.04)}
    .card{background:#111827;border:1px solid #1e293b;border-radius:14px;padding:22px;margin-bottom:18px}
    .legend{display:flex;gap:20px;margin-bottom:16px;font-size:13px}
    .legend span{padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px}
    """

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>指数估值仪表盘</title><style>{css}</style></head><body>
<h1>📊 指数估值仪表盘</h1>
<p class="sub">生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · PE分位 = 当前PE在历史中的位置 · 越低越便宜</p>

<div class="card">
<div class="legend">
<span style="background:#14532d;color:#86efac">🟢 低估 (分位≤20%)</span>
<span style="background:#1e3a5f;color:#93c5fd">🟡 偏低 (20-40%)</span>
<span style="background:#1e293b;color:#94a3b8">⚪ 合理 (40-60%)</span>
<span style="background:#78350f;color:#fcd34d">🟠 偏高 (60-80%)</span>
<span style="background:#7f1d1d;color:#fca5a5">🔴 高估 (分位>80%)</span>
</div>
<table>
<thead><tr><th>指数代码</th><th>名称</th><th>ETF</th><th>当前PE</th><th>PE分位</th><th>PE评级</th><th>PB分位</th></tr></thead>
<tbody>{rows if rows else '<tr><td colspan="7" style="color:#64748b;text-align:center;padding:30px">暂无估值数据，请先运行 菜单7→下载数据</td></tr>'}</tbody>
</table>
</div>
</body></html>"""
    return html


def show_valuation():
    """终端打印估值快照"""
    from src.console import table, ok, fail, warn

    snapshot = get_valuation_snapshot()
    if snapshot.empty:
        fail("暂无估值数据")
        return

    print()
    headers = ["指数", "名称", "PE", "PE分位", "PE评级", "PB分位"]
    rows = []
    for _, r in snapshot.iterrows():
        rows.append([
            r["指数"], r["名称"],
            str(r.get("PE", "N/A")), str(r.get("PE分位", "N/A")),
            str(r.get("PE评级", "-")), str(r.get("PB分位", "N/A")),
        ])

    table(headers, rows, title="📊 指数估值快照")

    # 投资建议
    buys = []
    for _, r in snapshot.iterrows():
        zone = str(r.get("PE评级", ""))
        if "低估" in zone:
            buys.append(f"{r['名称']}({r['指数']})")
    if buys:
        ok(f"低估机会: {', '.join(buys)}")
    else:
        warn("当前无明显低估机会，耐心等待。")
