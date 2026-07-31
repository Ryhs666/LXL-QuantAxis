"""
Fundamental Factors — value, quality, and growth signals.

This package provides both:
  - New institutional-grade BaseFactor subclasses (value.py, quality.py, growth.py)
  - Legacy FundamentalFactors class (backward compatible with v5.x)

Usage:
    from src.factors.fundamental import PEFactor, FundamentalFactors, fundamental
"""

# --- New institutional factors ---
from src.factors.fundamental.value import PEFactor, PBFactor, EVEBITDAFactor
from src.factors.fundamental.quality import ROEFactor, GrossMarginFactor, FreeCashFlowFactor
from src.factors.fundamental.growth import RevenueGrowthFactor, EPSGrowthFactor, ProfitGrowthFactor

# --- Legacy FundamentalFactors (v5.5) — preserved for backward compatibility ---

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


class FundamentalFactors:
    """A-share fundamental factor calculator (legacy v5.5).

    Provides PE, PB, ROE, and revenue growth retrieval via AKShare.
    This class is preserved for backward compatibility with existing code.
    For new code, prefer using the BaseFactor subclasses (PEFactor, ROEFactor, etc.).
    """

    def __init__(self):
        self._cache = {}

    # ---- Single stock retrieval ----

    def get_roe(self, symbol: str) -> Optional[float]:
        """ROE (TTM) — return on equity."""
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

    def get_pe(self, symbol: str) -> Optional[float]:
        """Trailing PE ratio."""
        try:
            import akshare as ak
            df = ak.stock_a_lg_indicator(symbol=symbol)
            if df is not None and not df.empty and 'pe' in df.columns:
                return float(df['pe'].iloc[-1]) if not pd.isna(df['pe'].iloc[-1]) else None
        except Exception:
            pass
        try:
            import akshare as ak
            df = ak.stock_a_indicator_lg(symbol=symbol)
            if df is not None and not df.empty:
                pe_col = [c for c in df.columns if 'pe' in str(c).lower()]
                if pe_col:
                    return float(df[pe_col[0]].iloc[-1]) if not pd.isna(df[pe_col[0]].iloc[-1]) else None
        except Exception:
            pass
        return None

    def get_pb(self, symbol: str) -> Optional[float]:
        """Price-to-Book ratio (latest quarter)."""
        try:
            import akshare as ak
            df = ak.stock_a_lg_indicator(symbol=symbol)
            if df is not None and not df.empty and 'pb' in df.columns:
                return float(df['pb'].iloc[-1]) if not pd.isna(df['pb'].iloc[-1]) else None
        except Exception:
            pass
        try:
            import akshare as ak
            df = ak.stock_a_indicator_lg(symbol=symbol)
            if df is not None and not df.empty:
                pb_col = [c for c in df.columns if 'pb' in str(c).lower()]
                if pb_col:
                    return float(df[pb_col[0]].iloc[-1]) if not pd.isna(df[pb_col[0]].iloc[-1]) else None
        except Exception:
            pass
        return None

    def get_revenue_growth(self, symbol: str) -> Optional[float]:
        """Revenue YoY growth rate."""
        try:
            import akshare as ak
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df is None or df.empty:
                return None
            rev_col = [c for c in df.columns if '营业收入' in str(c) and '同比' in str(c)]
            if not rev_col:
                rev_col = [c for c in df.columns if '营收' in str(c) and ('增长' in str(c) or '同比' in str(c))]
            if rev_col and len(df) > 0:
                val = df[rev_col[0]].iloc[0]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None

    def get_all_fundamentals(self, symbol: str) -> dict:
        """Get all fundamental factors for a single stock."""
        return {
            "ROE": self.get_roe(symbol),
            "PE": self.get_pe(symbol),
            "PB": self.get_pb(symbol),
            "营收增长率": self.get_revenue_growth(symbol),
        }

    # ---- Batch retrieval ----

    def fetch_batch(self, symbols: list, factor: str = "PE",
                    date: str = None) -> pd.DataFrame:
        """Batch fetch a single fundamental factor for multiple symbols."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        method_map = {
            "ROE": self.get_roe,
            "PE": self.get_pe,
            "PB": self.get_pb,
            "营收增长率": self.get_revenue_growth,
        }
        fetch_fn = method_map.get(factor, self.get_pe)

        data = {}
        for sym in symbols:
            try:
                val = fetch_fn(sym)
                data[sym] = val if val is not None else np.nan
            except Exception:
                data[sym] = np.nan

        df = pd.DataFrame([data], index=[date])
        df.index.name = "date"
        return df

    def fetch_all_factors(self, symbols: list,
                          date: str = None) -> pd.DataFrame:
        """Batch fetch all 4 fundamental factors for multiple symbols."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        results = {}
        for factor in ["ROE", "PE", "PB", "营收增长率"]:
            try:
                df = self.fetch_batch(symbols, factor, date)
                results[factor] = df
            except Exception:
                results[factor] = pd.DataFrame(
                    [[np.nan] * len(symbols)], index=[date], columns=symbols)

        all_dfs = []
        for factor, df in results.items():
            df_copy = df.copy()
            df_copy.columns = pd.MultiIndex.from_product([[factor], df.columns])
            all_dfs.append(df_copy)

        return pd.concat(all_dfs, axis=1)

    # ---- Normalization ----

    @staticmethod
    def normalize_pe(pe_series: pd.Series) -> pd.Series:
        """PE normalization: lower PE → higher score (0–1)."""
        result = pd.Series(0.5, index=pe_series.index)
        mask = pe_series.notna() & (pe_series > 0)
        valid = pe_series[mask]
        if len(valid) == 0:
            return result
        normalized = 1 / (1 + np.exp((valid - 25) / 15))
        result[mask] = normalized
        return result.clip(0, 1)

    @staticmethod
    def normalize_pb(pb_series: pd.Series) -> pd.Series:
        """PB normalization: lower PB → higher score (0–1)."""
        result = pd.Series(0.5, index=pb_series.index)
        mask = pb_series.notna() & (pb_series > 0)
        valid = pb_series[mask]
        if len(valid) == 0:
            return result
        normalized = 1 / (1 + np.exp((valid - 3) / 1.5))
        result[mask] = normalized
        return result.clip(0, 1)

    @staticmethod
    def normalize_roe(roe_series: pd.Series) -> pd.Series:
        """ROE normalization: higher ROE → higher score (0–1)."""
        result = pd.Series(0.5, index=roe_series.index)
        mask = roe_series.notna()
        valid = roe_series[mask]
        if len(valid) == 0:
            return result
        normalized = 1 / (1 + np.exp(-(valid - 10) / 8))
        result[mask] = normalized
        return result.clip(0, 1)

    @staticmethod
    def normalize_revenue_growth(growth_series: pd.Series) -> pd.Series:
        """Revenue growth normalization: higher growth → higher score (0–1)."""
        result = pd.Series(0.5, index=growth_series.index)
        mask = growth_series.notna()
        valid = growth_series[mask]
        if len(valid) == 0:
            return result
        normalized = 1 / (1 + np.exp(-(valid - 10) / 15))
        result[mask] = normalized
        return result.clip(0, 1)


# Global singleton instance (backward compatible)
fundamental = FundamentalFactors()


__all__ = [
    # New institutional factors
    "PEFactor",
    "PBFactor",
    "EVEBITDAFactor",
    "ROEFactor",
    "GrossMarginFactor",
    "FreeCashFlowFactor",
    "RevenueGrowthFactor",
    "EPSGrowthFactor",
    "ProfitGrowthFactor",
    # Legacy
    "FundamentalFactors",
    "fundamental",
]
