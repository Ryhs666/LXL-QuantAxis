"""
可视化图表

- 资金曲线图
- 回撤曲线
- 月度收益热力图
- 盈亏分布直方图
"""

import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from src.models.trade import TradeRepository


def equity_curve(daily_values: List[dict],
                 title: str = "资金曲线",
                 save_path: str = None):
    """
    绘制资金曲线和回撤图

    参数:
        daily_values: 每日净值记录（来自回测 engine）
        title: 图表标题
        save_path: 保存路径，为 None 则显示交互式图表
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if not daily_values:
        print("⚠️ 没有每日净值数据，无法绘图。")
        return

    df = pd.DataFrame(daily_values)
    df["date"] = pd.to_datetime(df["date"])

    # 计算回撤
    df["peak"] = df["total_value"].cummax()
    df["drawdown"] = (df["total_value"] - df["peak"]) / df["peak"] * 100

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(title, "回撤 (%)"),
    )

    # 资金曲线
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["total_value"],
                   mode="lines", name="总资产",
                   line=dict(color="#2563eb", width=2)),
        row=1, col=1,
    )

    # 初始资金参考线
    if daily_values:
        initial = daily_values[0]["total_value"]
        fig.add_hline(y=initial, line_dash="dash", line_color="gray",
                       annotation_text="初始资金", row=1, col=1)

    # 回撤
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["drawdown"],
                   mode="lines", name="回撤",
                   fill="tozeroy",
                   line=dict(color="#dc2626", width=1)),
        row=2, col=1,
    )

    fig.update_layout(
        height=600,
        hovermode="x unified",
        showlegend=False,
    )
    fig.update_yaxes(title_text="总资产 (¥)", row=1, col=1)
    fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)

    if save_path:
        fig.write_html(save_path)
        print(f"  📈 图表已保存: {save_path}")
    else:
        fig.show()

    return fig


def monthly_returns_heatmap(daily_values: List[dict],
                            save_path: str = None):
    """
    月度收益热力图

    参数:
        daily_values: 每日净值记录
        save_path: 保存路径
    """
    import plotly.graph_objects as go
    import numpy as np

    if not daily_values:
        print("⚠️ 没有每日净值数据，无法绘图。")
        return

    df = pd.DataFrame(daily_values)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # 计算日收益率
    df["return"] = df["total_value"].pct_change()

    # 按月汇总
    monthly = df["return"].resample("ME").apply(
        lambda x: (1 + x).prod() - 1
    ) * 100

    if monthly.empty:
        print("⚠️ 数据不足以生成月度热力图。")
        return

    # 构建热力图矩阵
    monthly_df = monthly.to_frame(name="return")
    monthly_df["year"] = monthly_df.index.year
    monthly_df["month"] = monthly_df.index.month

    pivot = monthly_df.pivot(index="year", columns="month", values="return")
    pivot = pivot.sort_index(ascending=False)

    month_names = ["1月", "2月", "3月", "4月", "5月", "6月",
                   "7月", "8月", "9月", "10月", "11月", "12月"]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[month_names[m - 1] for m in pivot.columns],
        y=pivot.index.astype(str),
        text=[[f"{v:+.1f}%" if not np.isnan(v) else "" for v in row]
              for row in pivot.values],
        texttemplate="%{text}",
        colorscale=[
            [0, "#dc2626"],    # 负收益 → 红色
            [0.5, "#ffffff"],  # 零 → 白色
            [1, "#16a34a"],    # 正收益 → 绿色
        ],
        zmid=0,
        colorbar=dict(title="收益率 %"),
    ))

    fig.update_layout(
        title="月度收益热力图",
        height=400,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"  📈 热力图已保存: {save_path}")
    else:
        fig.show()

    return fig


def pnl_distribution(pnl_list: List[dict],
                     save_path: str = None):
    """
    盈亏分布直方图

    参数:
        pnl_list: 盈亏列表（来自 repo.get_all_pnl()）
        save_path: 保存路径
    """
    import plotly.graph_objects as go

    if not pnl_list:
        print("⚠️ 没有已完成的交易，无法生成分布图。")
        return

    pnl_values = [p["net_pnl"] for p in pnl_list]

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=pnl_values,
        nbinsx=20,
        marker=dict(
            color=["#16a34a" if v >= 0 else "#dc2626" for v in pnl_values]
        ),
        name="盈亏分布",
    ))

    # 均值线
    mean_pnl = sum(pnl_values) / len(pnl_values)
    fig.add_vline(x=mean_pnl, line_dash="dash", line_color="gray",
                   annotation_text=f"均值 ¥{mean_pnl:+,.0f}")

    fig.update_layout(
        title="盈亏分布",
        xaxis_title="盈亏 (¥)",
        yaxis_title="次数",
        height=400,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"  📈 分布图已保存: {save_path}")
    else:
        fig.show()

    return fig


def portfolio_charts(daily_values: List[dict] = None,
                     pnl_list: List[dict] = None,
                     output_dir: str = None):
    """
    一键生成全套图表

    参数:
        daily_values: 每日净值（来自回测）
        pnl_list: 实盘盈亏列表（来自数据库）
        output_dir: 输出目录，为 None 则显示交互式图表
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    charts = []

    if daily_values:
        path1 = os.path.join(output_dir, "equity_curve.html") if output_dir else None
        charts.append(("资金曲线", equity_curve(daily_values, save_path=path1)))

        if output_dir:
            path2 = os.path.join(output_dir, "monthly_heatmap.html")
            charts.append(("月度热力图", monthly_returns_heatmap(daily_values, save_path=path2)))
        else:
            charts.append(("月度热力图", monthly_returns_heatmap(daily_values)))

    if pnl_list:
        path3 = os.path.join(output_dir, "pnl_distribution.html") if output_dir else None
        charts.append(("盈亏分布", pnl_distribution(pnl_list, save_path=path3)))

    if output_dir:
        print(f"\n  ✅ 图表已全部保存到: {output_dir}/")

    return charts


def plot_from_backtest(result: dict, save_dir: str = None):
    """从回测结果生成图表"""
    portfolio = result.get("portfolio")
    if not portfolio:
        print("⚠️ 回测结果中没有 portfolio 数据。")
        return

    return portfolio_charts(
        daily_values=portfolio.daily_values,
        output_dir=save_dir,
    )
