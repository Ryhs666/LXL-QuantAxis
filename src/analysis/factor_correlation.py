# -*- coding: utf-8 -*-
"""
Factor Correlation Analyzer — 因子相关性分析工具

功能:
  1. 计算因子间相关系数矩阵 (Pearson / Spearman)
  2. 绘制热力图
  3. 检测高相关冗余因子对
  4. 对接项目因子体系 (FactorCalculator + FACTOR_REGISTRY)

使用方式:
    from src.analysis.factor_correlation import analyze_factor_correlation
    corr, pairs = analyze_factor_correlation("600519", "2024-01-01")
"""

import os
from typing import List, Tuple, Optional, Dict
from datetime import datetime

import pandas as pd
import numpy as np


def compute_correlation_matrix(
    factor_df: pd.DataFrame,
    factors: List[str] = None,
    method: str = "pearson",
) -> pd.DataFrame:
    """
    计算因子相关系数矩阵。

    Args:
        factor_df: 因子 DataFrame (index=date, columns=factor_names)
        factors:   指定因子列表, None=全部列
        method:    'pearson' 或 'spearman'

    Returns:
        相关系数矩阵
    """
    if factors is None:
        factors = [c for c in factor_df.columns
                   if (isinstance(c, str) and not c.startswith("_"))
                   and c not in ("date", "symbol")]

    available = [f for f in factors if f in factor_df.columns]
    if len(available) < 2:
        print(f"[FactorCorr] 可用因子不足: {len(available)}")
        return pd.DataFrame()

    # 截取尾部数据 (前部因滚动窗口有大量 NaN)
    # 取最后 min(500, len) 行, 在此期间大多数因子已完成预热
    tail = factor_df[available].tail(min(500, len(factor_df)))
    data = tail.dropna(axis=0, how="any")

    # 如果全行 drop 后数据仍不足, 用 pairwise 策略: 每对因子独立取有效行
    if len(data) < 20:
        print(f"[FactorCorr] 全因子对齐后仅 {len(data)} 行, 尝试 pairwise 计算...")
        return _pairwise_corr(tail, available, method)

    return data.corr(method=method)


def _pairwise_corr(df: pd.DataFrame, factors: List[str], method: str) -> pd.DataFrame:
    """Pairwise 相关性: 每对因子用各自的共有有效行计算"""
    n = len(factors)
    corr = pd.DataFrame(np.eye(n), index=factors, columns=factors)
    for i in range(n):
        for j in range(i + 1, n):
            pair = df[[factors[i], factors[j]]].dropna()
            if len(pair) >= 20:
                val = pair.corr(method=method).iloc[0, 1]
            else:
                val = np.nan
            corr.iloc[i, j] = val
            corr.iloc[j, i] = val
    return corr


def find_high_corr_pairs(
    corr_matrix: pd.DataFrame,
    threshold: float = 0.8,
) -> List[Tuple[str, str, float]]:
    """
    找出 |相关系数| > threshold 的因子对。

    Returns:
        [(因子A, 因子B, 相关系数), ...], 按 |r| 降序排列
    """
    high_pairs = []
    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr_matrix.iloc[i, j]
            if abs(val) > threshold:
                high_pairs.append((cols[i], cols[j], round(val, 3)))
    high_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return high_pairs


def suggest_redundant_removal(
    corr_matrix: pd.DataFrame,
    threshold: float = 0.8,
) -> List[str]:
    """
    基于相关性推荐移除的冗余因子。

    策略: 对于每对高相关因子, 移除与其他因子平均相关性更高的那个。
    """
    pairs = find_high_corr_pairs(corr_matrix, threshold)
    if not pairs:
        return []

    removed = set()
    suggestions = []

    for a, b, r in pairs:
        if a in removed or b in removed:
            continue
        # 计算每个因子与其他所有因子的平均 |r|
        avg_a = corr_matrix[a].drop([a, b]).abs().mean()
        avg_b = corr_matrix[b].drop([a, b]).abs().mean()
        # 移除平均相关性更高的那个 (更冗余)
        to_remove = a if avg_a > avg_b else b
        removed.add(to_remove)
        suggestions.append({
            "factor": to_remove,
            "correlated_with": b if to_remove == a else a,
            "correlation": r,
            "avg_corr_of_removed": round(avg_a if to_remove == a else avg_b, 3),
            "avg_corr_of_kept": round(avg_b if to_remove == a else avg_a, 3),
        })

    return suggestions


def plot_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    save_path: str = None,
    figsize: tuple = (14, 12),
    method: str = "pearson",
    title: str = "",
) -> str:
    """
    绘制因子相关性热力图, 返回 HTML 字符串 (Plotly, 免 GUI 依赖)。

    使用 Plotly 而非 seaborn/matplotlib, 因为:
      1. 无需 GUI / DISPLAY 环境变量
      2. 输出可直接嵌入 Dashboard
      3. 项目已有 plotly 依赖
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        print("[FactorCorr] plotly 未安装, 无法绘图")
        return ""

    if corr_matrix.empty:
        return ""

    labels = list(corr_matrix.columns)
    z = corr_matrix.values

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=labels,
        y=labels,
        zmin=-1, zmax=1,
        colorscale="RdBu_r",
        text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont={"size": 9},
        hoverongaps=False,
    ))

    title_text = title or f"Factor Correlation Matrix (method={method})"
    fig.update_layout(
        title={"text": title_text, "font": {"size": 16, "color": "#f1f5f9"}},
        width=figsize[0] * 80,
        height=figsize[1] * 70,
        paper_bgcolor="#0b0f1a",
        plot_bgcolor="#0b0f1a",
        xaxis={"side": "bottom", "tickangle": 45, "tickfont": {"size": 9, "color": "#94a3b8"}},
        yaxis={"tickfont": {"size": 9, "color": "#94a3b8"}},
        margin={"l": 120, "r": 40, "t": 60, "b": 100},
    )

    if save_path:
        # 保存为 HTML (交互式) 和 PNG (静态)
        html_path = save_path.replace(".png", ".html")
        fig.write_html(html_path)
        try:
            fig.write_image(save_path, scale=2)
        except Exception:
            pass  # kaleido 未安装时跳过 PNG
        print(f"[FactorCorr] 热力图已保存: {html_path}")
        return html_path

    return pio.to_html(fig, full_html=False)


# ═══════════════════════════════════════════
# 对接项目因子体系
# ═══════════════════════════════════════════

def analyze_factor_correlation(
    symbol: str,
    start_date: str = "2024-01-01",
    market: str = "A股",
    method: str = "pearson",
    threshold: float = 0.8,
    save_dir: str = None,
) -> dict:
    """
    一键因子相关性分析 (对接 FactorCalculator)。

    Args:
        symbol:     股票代码
        start_date: 起始日期
        market:     市场
        method:     相关性方法
        threshold:  高相关阈值
        save_dir:   热力图保存目录 (None=不保存)

    Returns:
        {
            "corr_matrix": DataFrame,
            "high_pairs": [(a, b, r), ...],
            "suggestions": [{factor, correlated_with, correlation, ...}, ...],
            "factor_count": int,
            "html_path": str or None,
        }
    """
    from src.backtest.data_feed import get_data
    from src.factors.definitions import FactorCalculator, FACTOR_REGISTRY

    data = get_data(symbol, market, start_date=start_date)
    if data is None or len(data) < 60:
        return {"error": f"数据不足: {symbol}"}

    calc = FactorCalculator(data)
    factor_df = calc.compute_all()

    # 过滤掉非数值列
    numeric_cols = [c for c in factor_df.columns
                    if c not in ("date", "symbol")
                    and pd.api.types.is_numeric_dtype(factor_df[c])]
    factor_df = factor_df[numeric_cols]

    corr_matrix = compute_correlation_matrix(factor_df, method=method)
    high_pairs = find_high_corr_pairs(corr_matrix, threshold)
    suggestions = suggest_redundant_removal(corr_matrix, threshold)

    # 保存热力图
    html_path = None
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = plot_correlation_heatmap(
            corr_matrix,
            save_path=os.path.join(save_dir, f"factor_corr_{symbol}_{ts}.png"),
            method=method,
            title=f"因子相关性 — {symbol} ({method}, n={len(corr_matrix)})",
        )

    return {
        "symbol": symbol,
        "factor_count": len(corr_matrix),
        "corr_matrix": corr_matrix,
        "high_pairs": high_pairs,
        "suggestions": suggestions,
        "html_path": html_path,
    }


def print_correlation_report(result: dict):
    """打印可读的相关性分析报告"""
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return

    print(f"\n═══ 因子相关性报告: {result['symbol']} ═══")
    print(f"  因子数量: {result['factor_count']}")
    print(f"  高相关对 (|r|>0.8): {len(result['high_pairs'])} 对")

    if result["high_pairs"]:
        print(f"\n── TOP 10 高相关因子对 ──")
        for a, b, r in result["high_pairs"][:10]:
            bar = "█" * min(20, int(abs(r) * 20))
            print(f"  {a:<20} ↔ {b:<20}  r={r:+.3f}  {bar}")

    if result["suggestions"]:
        print(f"\n── 建议移除的冗余因子 ──")
        for s in result["suggestions"]:
            print(f"  ✂ {s['factor']} (与 {s['correlated_with']} 相关 {s['correlation']:.2f}, "
                  f"平均|r|: {s['avg_corr_of_removed']:.2f} vs {s['avg_corr_of_kept']:.2f})")

    if result.get("html_path"):
        print(f"\n  热力图: {result['html_path']}")


# ═══════════════════════════════════════════
# CLI / 测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "600519"
    result = analyze_factor_correlation(symbol, save_dir="D:/trading_data/charts")
    print_correlation_report(result)
