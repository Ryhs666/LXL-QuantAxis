"""
Growth Factors — revenue and earnings expansion signals.

Factors:
  - growth_revenue: Year-over-year revenue growth rate
  - growth_eps: Year-over-year earnings per share growth
  - growth_profit: Year-over-year net profit growth

Growth factors capture the trajectory of a company's financial performance.
Combined with value factors, they form the core of GARP (Growth At a
Reasonable Price) strategies.
"""

import pandas as pd
import numpy as np
from typing import Optional

from src.factors.core.factor_base import BaseFactor


class RevenueGrowthFactor(BaseFactor):
    """Year-over-year revenue growth — top-line expansion.

    Revenue growth is the most fundamental measure of business expansion.
    Center at 10% (rough threshold for "growth" companies in A-shares).
    Above 20% = high growth, below 0% = contracting.
    """

    name = "growth_revenue"
    category = "growth"
    display_name = "Revenue Growth (YoY)"
    _description = "Year-over-year revenue growth rate. Top-line expansion is the most fundamental growth metric. Center at 10%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "revenue_growth" in data.columns:
            rg = data["revenue_growth"].astype(float)
            result = self._sigmoid(rg, center=10, steepness=1/15)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch revenue growth YoY for a single A-share symbol."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            rev_col = [c for c in df.columns
                       if '营业收入' in str(c) and '同比' in str(c)]
            if not rev_col:
                rev_col = [c for c in df.columns
                           if '营收' in str(c) and ('增长' in str(c) or '同比' in str(c))]
            if rev_col and len(df) > 0:
                val = df[rev_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None


class EPSGrowthFactor(BaseFactor):
    """Year-over-year earnings per share growth — bottom-line expansion.

    EPS growth shows how quickly a company is growing its per-share earnings.
    More meaningful than revenue growth alone because it accounts for dilution
    and profitability. Center at 10%.
    """

    name = "growth_eps"
    category = "growth"
    display_name = "EPS Growth (YoY)"
    _description = "Year-over-year earnings per share growth. Bottom-line growth accounting for share dilution. Center at 10%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "eps_growth" in data.columns:
            eg = data["eps_growth"].astype(float)
            result = self._sigmoid(eg, center=10, steepness=1/15)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch EPS growth YoY for a single A-share symbol."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            eps_col = [c for c in df.columns
                       if '每股收益' in str(c) and '同比' in str(c)]
            if not eps_col:
                eps_col = [c for c in df.columns
                           if 'EPS' in str(c).upper() and '增长' in str(c)]
            if eps_col and len(df) > 0:
                val = df[eps_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None


class ProfitGrowthFactor(BaseFactor):
    """Year-over-year net profit growth — the ultimate bottom line.

    Net profit growth captures the full income statement impact —
    revenue growth minus cost growth minus one-time items.
    Center at 10%.
    """

    name = "growth_profit"
    category = "growth"
    display_name = "Net Profit Growth (YoY)"
    _description = "Year-over-year net profit growth rate. The ultimate bottom-line growth measure. Center at 10%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "profit_growth" in data.columns:
            pg = data["profit_growth"].astype(float)
            result = self._sigmoid(pg, center=10, steepness=1/15)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch net profit growth YoY for a single A-share symbol."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            profit_col = [c for c in df.columns
                          if '净利润' in str(c) and '同比' in str(c)]
            if not profit_col:
                profit_col = [c for c in df.columns
                              if '净利' in str(c) and '增长' in str(c)]
            if profit_col and len(df) > 0:
                val = df[profit_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None
