"""
组合收益与风险指标 v1.1

提供:
  - prices_to_returns:      价格 → 收益率（simple / log）
  - validate_weights:       权重校验与对齐
  - portfolio_return_series: 组合加权收益率序列
  - cumulative_return:      累计收益率
  - annualized_return:      年化收益率
  - annualized_volatility:  年化波动率
  - sharpe_ratio:           夏普比率
  - max_drawdown:           最大回撤
  - PortfolioMetrics:       指标汇总（frozen dataclass）
  - summarize_portfolio:    一键计算全部指标
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Union

import numpy as np
import pandas as pd


# ============================================================
# 内部校验辅助
# ============================================================

def _validate_returns(returns: pd.Series, min_obs: int = 1) -> None:
    """统一校验收益率 Series。

    检查: 类型、长度、数值 dtype、NaN、inf、单期收益率 ≥ -1。
    """
    if not isinstance(returns, pd.Series):
        raise TypeError(f"returns 必须是 Series，收到: {type(returns).__name__}")
    if len(returns) < min_obs:
        raise ValueError(
            f"returns 至少需要 {min_obs} 个观测值，当前: {len(returns)}"
        )
    if not pd.api.types.is_numeric_dtype(returns):
        raise ValueError("returns 必须是数值 dtype")
    if returns.isna().any():
        raise ValueError("returns 包含 NaN 值")
    # NaN 已排除，此处只捕获 inf
    if not np.isfinite(returns.values).all():
        raise ValueError("returns 包含 inf 值")
    if (returns < -1).any():
        raise ValueError("单期收益率不得小于 -1")


def _validate_periods_per_year(periods_per_year: float) -> None:
    """校验 periods_per_year：必须是有限正数。"""
    if not isinstance(periods_per_year, (int, float)):
        raise TypeError(
            f"periods_per_year 必须是数值，收到: {type(periods_per_year).__name__}"
        )
    if not np.isfinite(periods_per_year):
        raise ValueError(f"periods_per_year 必须是有限值，收到: {periods_per_year}")
    if periods_per_year <= 0:
        raise ValueError(
            f"periods_per_year 必须为正数，收到: {periods_per_year}"
        )


def _validate_risk_free_rate(risk_free_rate: float) -> None:
    """校验 risk_free_rate：必须是有限数值且 > -1。"""
    if not isinstance(risk_free_rate, (int, float)):
        raise TypeError(
            f"risk_free_rate 必须是数值，收到: {type(risk_free_rate).__name__}"
        )
    if not np.isfinite(risk_free_rate):
        raise ValueError(f"risk_free_rate 必须是有限值，收到: {risk_free_rate}")
    if risk_free_rate <= -1:
        raise ValueError(
            f"risk_free_rate 必须大于 -1，收到: {risk_free_rate}"
        )


def _rf_per_period(risk_free_rate: float, periods_per_year: float) -> float:
    """复利方式换算每期无风险收益率。"""
    return (1 + risk_free_rate) ** (1 / periods_per_year) - 1


# ============================================================
# 价格 → 收益率
# ============================================================

def prices_to_returns(
    prices: pd.DataFrame,
    method: str = "simple",
) -> pd.DataFrame:
    """将价格 DataFrame 转为收益率 DataFrame。

    Args:
        prices: 每一列代表一个资产，每一行代表一个时间点。
        method: "simple" → pct_change; "log" → log(p_t / p_{t-1})

    Returns:
        收益率 DataFrame，列名和顺序与输入一致，首行 NaN 已删除。

    Raises:
        TypeError:  method 不是字符串。
        ValueError: 空数据、行数不足、非数值列、重复列、NaN/inf、
                    非法 method、log 模式非正价格。
    """
    if not isinstance(prices, pd.DataFrame):
        raise TypeError(f"prices 必须是 DataFrame，收到: {type(prices).__name__}")
    if prices.empty:
        raise ValueError("prices 不能为空")
    if len(prices) < 2:
        raise ValueError(f"prices 至少需要 2 个时间点，当前: {len(prices)}")
    if prices.columns.duplicated().any():
        raise ValueError("prices 包含重复的资产列名")

    # 检查所有列均为数值
    non_numeric = [
        c for c in prices.columns
        if not pd.api.types.is_numeric_dtype(prices[c])
    ]
    if non_numeric:
        raise ValueError(f"prices 包含非数值列: {non_numeric}")

    # 检查 NaN 和 inf
    if prices.isna().any().any():
        raise ValueError("prices 包含 NaN 值")
    if not np.isfinite(prices.values).all():
        raise ValueError("prices 包含 inf 值")

    # 校验 method 类型
    if not isinstance(method, str):
        raise TypeError(
            f"method 必须是字符串，收到: {type(method).__name__}"
        )

    method = method.strip().lower()
    if method not in ("simple", "log"):
        raise ValueError(f"不支持的 method: {method!r}，可选: simple, log")

    if method == "log" and (prices <= 0).any().any():
        raise ValueError("log 收益率要求所有价格严格大于 0")

    if method == "simple":
        result = prices.pct_change(fill_method=None)
    else:
        result = np.log(prices / prices.shift(1))

    # 删除首行缺失值
    result = result.dropna(how="all")

    # 计算结果不得包含 NaN 或 inf
    if result.isna().any().any():
        raise ValueError("计算结果包含 NaN 值")
    if not np.isfinite(result.values).all():
        raise ValueError("计算结果包含 inf 值")

    return result


# ============================================================
# 权重校验
# ============================================================

def validate_weights(
    weights: Union[dict, Mapping, pd.Series],
    assets: list,
    tolerance: float = 1e-8,
) -> pd.Series:
    """校验并对齐组合权重。

    Args:
        weights:   资产权重（dict / Mapping / pd.Series）。
        assets:    目标资产列表（顺序即为输出顺序）。
        tolerance: 权重和允许的浮点误差。

    Returns:
        按照 assets 顺序排列的权重 Series。

    Raises:
        TypeError:  weights 类型不合法、tolerance 不是数值。
        ValueError: 资产不匹配、权重非法、和不等于 1、tolerance 非法。
    """
    if assets is None or len(assets) == 0:
        raise ValueError("assets 不能为空")
    if len(assets) != len(set(assets)):
        raise ValueError("assets 列表包含重复项")

    # 校验 tolerance
    if not isinstance(tolerance, (int, float)):
        raise TypeError(
            f"tolerance 必须是数值，收到: {type(tolerance).__name__}"
        )
    if not np.isfinite(tolerance):
        raise ValueError(f"tolerance 必须是有限值，收到: {tolerance}")
    if tolerance < 0:
        raise ValueError(f"tolerance 不能为负，收到: {tolerance}")

    if isinstance(weights, pd.Series):
        w = weights.copy()
    elif isinstance(weights, (dict, Mapping)):
        w = pd.Series(weights)
    else:
        raise TypeError(
            f"weights 必须是 dict、Mapping 或 Series，收到: {type(weights).__name__}"
        )

    # 资产集合必须完全匹配
    w_assets = set(w.index)
    a_assets = set(assets)
    if w_assets != a_assets:
        missing = a_assets - w_assets
        extra = w_assets - a_assets
        msg_parts = []
        if missing:
            msg_parts.append(f"缺少资产: {sorted(missing)}")
        if extra:
            msg_parts.append(f"多余资产: {sorted(extra)}")
        raise ValueError("资产集合不匹配: " + "; ".join(msg_parts))

    # 按 assets 顺序对齐
    w = w.reindex(assets)

    # 权重必须为数值类型（拒绝字符串、布尔、对象等）
    if pd.api.types.is_bool_dtype(w):
        raise ValueError(
            "权重值必须为数值类型，不允许布尔值"
        )
    if not pd.api.types.is_numeric_dtype(w):
        raise ValueError(
            "权重值必须为数值类型，不允许字符串或其他非数值"
        )

    # 检查均为有限数值
    if not np.isfinite(w.values).all():
        bad = w[~np.isfinite(w)].index.tolist()
        raise ValueError(f"权重包含非法值 (NaN / inf): {bad}")

    # long-only
    if (w < 0).any():
        bad = w[w < 0].index.tolist()
        raise ValueError(f"权重不得为负: {bad}")

    # 权重和 = 1
    total = w.sum()
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"权重和必须为 1，当前和为 {total:.10f}（容差 {tolerance}）"
        )

    return w


# ============================================================
# 组合加权收益率序列
# ============================================================

def portfolio_return_series(
    returns: pd.DataFrame,
    weights: Union[dict, Mapping, pd.Series],
) -> pd.Series:
    """计算组合加权收益率序列。

    Args:
        returns: 各资产收益率 DataFrame（列 = 资产，行 = 时间）。
        weights: 资产权重。

    Returns:
        命名为 "portfolio_return" 的 Series，保留原索引。
    """
    if not isinstance(returns, pd.DataFrame):
        raise TypeError(f"returns 必须是 DataFrame，收到: {type(returns).__name__}")
    if returns.empty:
        raise ValueError("returns 不能为空")

    # 校验权重
    w = validate_weights(weights, list(returns.columns))

    # 检查数值列
    non_numeric = [
        c for c in returns.columns
        if not pd.api.types.is_numeric_dtype(returns[c])
    ]
    if non_numeric:
        raise ValueError(f"returns 包含非数值列: {non_numeric}")

    # 检查 NaN / inf
    if returns.isna().any().any():
        raise ValueError("returns 包含 NaN 值")
    if not np.isfinite(returns.values).all():
        raise ValueError("returns 包含 inf 值")

    # 加权求和
    port = returns.dot(w)
    port.name = "portfolio_return"
    return port


# ============================================================
# 累计收益率
# ============================================================

def cumulative_return(returns: pd.Series) -> float:
    """计算累计收益率（复利）。

    Args:
        returns: 组合收益率 Series。

    Returns:
        累计收益率 float。
    """
    _validate_returns(returns, min_obs=1)
    return float(np.prod(1 + returns) - 1)


# ============================================================
# 年化收益率
# ============================================================

def annualized_return(
    returns: pd.Series,
    periods_per_year: float = 252,
) -> float:
    """计算年化收益率（复利）。

    Args:
        returns:           组合收益率 Series。
        periods_per_year:  每年交易天数（默认 252）。

    Returns:
        年化收益率 float。
    """
    _validate_returns(returns, min_obs=1)
    _validate_periods_per_year(periods_per_year)

    cum = np.prod(1 + returns)
    if cum <= 0:
        raise ValueError("累计净值非正，无法计算年化收益率")

    n = len(returns)
    return float(cum ** (periods_per_year / n) - 1)


# ============================================================
# 年化波动率
# ============================================================

def annualized_volatility(
    returns: pd.Series,
    periods_per_year: float = 252,
) -> float:
    """计算年化波动率（样本标准差 ddof=1）。

    Args:
        returns:           组合收益率 Series。
        periods_per_year:  每年交易天数（默认 252）。

    Returns:
        年化波动率 float。
    """
    _validate_returns(returns, min_obs=2)
    _validate_periods_per_year(periods_per_year)

    std = returns.std(ddof=1)
    return float(std * np.sqrt(periods_per_year))


# ============================================================
# 夏普比率
# ============================================================

def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> float:
    """计算年化夏普比率。

    使用超额收益均值和样本标准差计算。

    Args:
        returns:           组合收益率 Series。
        risk_free_rate:    年化无风险利率（默认 0）。
        periods_per_year:  每年交易天数（默认 252）。

    Returns:
        年化夏普比率 float。

    Raises:
        ValueError: 波动率为 0（无法计算比率）。
    """
    _validate_returns(returns, min_obs=2)
    _validate_periods_per_year(periods_per_year)
    _validate_risk_free_rate(risk_free_rate)

    # 复利方式换算每期无风险收益率
    rf_per_period = _rf_per_period(risk_free_rate, periods_per_year)
    excess = returns - rf_per_period

    std_excess = excess.std(ddof=1)

    # 浮点近零判断，避免常数收益率产生 inf
    if np.isclose(std_excess, 0.0, atol=1e-12):
        raise ValueError("波动率接近 0，无法计算 Sharpe Ratio")

    mean_excess = excess.mean()

    # 年化
    return float((mean_excess / std_excess) * np.sqrt(periods_per_year))


# ============================================================
# 最大回撤
# ============================================================

def max_drawdown(returns: pd.Series) -> float:
    """计算最大回撤。

    根据组合收益率生成净值曲线，计算相对历史高点的最大回撤。

    Args:
        returns: 组合收益率 Series。

    Returns:
        最大回撤 float（≤ 0；全程上涨时返回 0.0）。
    """
    _validate_returns(returns, min_obs=1)

    # 构建净值曲线，初始值 1.0 作为起点峰值
    eq_values = np.concatenate([[1.0], (1 + returns).values])
    cum_eq = np.cumprod(eq_values)
    running_max = np.maximum.accumulate(cum_eq)
    drawdown = (cum_eq - running_max) / running_max
    mdd = drawdown.min()
    return float(min(mdd, 0.0))


# ============================================================
# 指标汇总
# ============================================================

@dataclass(frozen=True)
class PortfolioMetrics:
    """组合指标汇总（不可变）。"""

    cumulative_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    observation_count: int


def summarize_portfolio(
    returns: pd.DataFrame,
    weights: Union[dict, Mapping, pd.Series],
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> PortfolioMetrics:
    """一键计算全部组合指标。

    先生成组合收益率序列，再调用各公共指标函数。

    Args:
        returns:           各资产收益率 DataFrame。
        weights:           资产权重。
        risk_free_rate:    年化无风险利率。
        periods_per_year:  每年交易天数。

    Returns:
        PortfolioMetrics（frozen dataclass）。
    """
    _validate_risk_free_rate(risk_free_rate)
    _validate_periods_per_year(periods_per_year)

    port_returns = portfolio_return_series(returns, weights)

    return PortfolioMetrics(
        cumulative_return=cumulative_return(port_returns),
        annualized_return=annualized_return(port_returns, periods_per_year),
        annualized_volatility=annualized_volatility(port_returns, periods_per_year),
        sharpe_ratio=sharpe_ratio(port_returns, risk_free_rate, periods_per_year),
        max_drawdown=max_drawdown(port_returns),
        observation_count=len(port_returns),
    )
