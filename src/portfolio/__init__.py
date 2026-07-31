"""
用户持仓管理与组合指标模块

用法:
    from src.portfolio import PortfolioManager
    pm = PortfolioManager(user_id=1)
    pm.add_or_update("601398", 1000, 5.50)
    df = pm.get_all()

    from src.portfolio import summarize_portfolio, cumulative_return
    metrics = summarize_portfolio(returns_df, weights)
"""

from src.portfolio.UserPortfolioManager import PortfolioManager
from src.portfolio.metrics import (
    prices_to_returns,
    validate_weights,
    portfolio_return_series,
    cumulative_return,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    max_drawdown,
    PortfolioMetrics,
    summarize_portfolio,
)

__all__ = [
    "PortfolioManager",
    "prices_to_returns",
    "validate_weights",
    "portfolio_return_series",
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
    "max_drawdown",
    "PortfolioMetrics",
    "summarize_portfolio",
]
