"""
Quality Factors — profitability and financial health signals.

Factors:
  - quality_roe: Return on Equity (higher = more efficient capital use)
  - quality_gross_margin: Gross profit margin (higher = pricing power)
  - quality_fcf: Free Cash Flow yield (higher = cash generation ability)

Quality factors identify companies with durable competitive advantages
("economic moats") — a cornerstone of institutional fundamental analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional

from src.factors.core.factor_base import BaseFactor


class ROEFactor(BaseFactor):
    """Return on Equity — Buffett's favorite metric.

    ROE measures how efficiently a company turns shareholder equity into profit.
    High and stable ROE (>15%) signals durable competitive advantage.
    Center at 10% (roughly risk-free rate + equity premium).
    """

    name = "quality_roe"
    category = "quality"
    display_name = "Return on Equity (ROE)"
    _description = "Return on Equity — measures capital efficiency. Higher ROE = more profit per unit of shareholder equity. Center at 10%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "ROE" in data.columns:
            roe = data["ROE"].astype(float)
            result = self._sigmoid(roe, center=10, steepness=1/8)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch ROE (TTM) for a single A-share symbol from AKShare."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            roe_col = [c for c in df.columns if '净资产收益率' in str(c) and '摊薄' not in str(c)]
            if not roe_col:
                roe_col = [c for c in df.columns if 'ROE' in str(c).upper()]
            if roe_col and len(df) > 0:
                val = df[roe_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None


class GrossMarginFactor(BaseFactor):
    """Gross Profit Margin — measures pricing power and cost efficiency.

    High gross margin (>40%) indicates strong pricing power or low production costs.
    Center at 30% (approximate A-share median).
    """

    name = "quality_gross_margin"
    category = "quality"
    display_name = "Gross Profit Margin"
    _description = "Gross profit margin = (Revenue - COGS) / Revenue. Measures pricing power and production efficiency. Center at 30%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "gross_margin" in data.columns:
            gm = data["gross_margin"].astype(float)
            result = self._sigmoid(gm, center=30, steepness=1/12)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch gross margin for a single A-share symbol."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            gm_col = [c for c in df.columns if '毛利率' in str(c) or 'Gross Margin' in str(c)]
            if gm_col and len(df) > 0:
                val = df[gm_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None


class FreeCashFlowFactor(BaseFactor):
    """Free Cash Flow Yield — cash generation relative to market value.

    FCF Yield = Free Cash Flow / Market Cap.
    Unlike earnings, FCF is harder to manipulate and represents real cash
    available to shareholders. Higher = better. Center at 3%.
    """

    name = "quality_fcf_yield"
    category = "quality"
    display_name = "Free Cash Flow Yield"
    _description = "Free Cash Flow / Market Cap. Measures real cash generation relative to price. Harder to manipulate than earnings. Center at 3%."
    source = "fundamental"
    higher_is_better = True

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "fcf_yield" in data.columns:
            fcf_y = data["fcf_yield"].astype(float)
            result = self._sigmoid(fcf_y, center=3, steepness=1/2)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Estimate FCF yield from available data.

        FCF ≈ Operating Cash Flow - CapEx
        Accurate computation requires detailed cash flow statement data.
        """
        # FCF yield requires detailed cash flow data not readily available
        # through free APIs for A-shares. Returns None as placeholder.
        return None
