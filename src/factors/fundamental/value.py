"""
Value Factors — valuation-based fundamental factors.

Factors:
  - value_pe: Price-to-Earnings ratio (lower = cheaper)
  - value_pb: Price-to-Book ratio (lower = cheaper)
  - value_ev_ebitda: Enterprise Value / EBITDA (lower = cheaper)

These are institutional-grade value factors commonly used in
quantitative equity research and factor models (Fama-French, etc.).
"""

import pandas as pd
import numpy as np
from typing import Optional

from src.factors.core.factor_base import BaseFactor


class PEFactor(BaseFactor):
    """Price-to-Earnings ratio — the most widely used valuation metric.

    Lower PE = cheaper relative to earnings. Normalized via sigmoid centered at 25
    (roughly the long-term A-share median). PE < 10 → high score (≈0.85+),
    PE > 100 → low score (≈0.05-).
    """

    name = "value_pe"
    category = "value"
    display_name = "Price-to-Earnings (PE)"
    _description = "Price-to-Earnings ratio, normalized so lower PE → higher score. Center at PE=25. A core value factor in institutional factor models."
    source = "fundamental"
    higher_is_better = False  # Lower PE is better value

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """For OHLCV data without PE, return neutral (0.5).

        Use fetch_pe(symbol) for actual fundamental data from AKShare.
        """
        # When used with OHLCV data, return neutral
        result = pd.Series(0.5, index=data.index)
        # If PE column exists (from joined data), use it
        if "PE" in data.columns:
            pe = data["PE"].astype(float)
            result = self._sigmoid(-pe, center=-25, steepness=1/15)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch PE ratio for a single A-share symbol from AKShare."""
        try:
            import akshare as ak
            df = ak.stock_a_lg_indicator(symbol=symbol)
            if df is not None and not df.empty and 'pe' in df.columns:
                return float(df['pe'].iloc[-1])
        except Exception:
            pass
        return None


class PBFactor(BaseFactor):
    """Price-to-Book ratio — value factor favored for financials and asset-heavy sectors.

    Lower PB = cheaper relative to book value. Center at PB=3.
    """

    name = "value_pb"
    category = "value"
    display_name = "Price-to-Book (PB)"
    _description = "Price-to-Book ratio, normalized so lower PB → higher score. Particularly relevant for financials, real estate, and asset-heavy sectors."
    source = "fundamental"
    higher_is_better = False

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "PB" in data.columns:
            pb = data["PB"].astype(float)
            result = self._sigmoid(-pb, center=-3, steepness=1/1.5)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Fetch PB ratio for a single A-share symbol from AKShare."""
        try:
            import akshare as ak
            df = ak.stock_a_lg_indicator(symbol=symbol)
            if df is not None and not df.empty and 'pb' in df.columns:
                return float(df['pb'].iloc[-1])
        except Exception:
            pass
        return None


class EVEBITDAFactor(BaseFactor):
    """Enterprise Value / EBITDA — capital-structure-neutral valuation.

    Unlike PE, EV/EBITDA accounts for debt and is comparable across
    companies with different capital structures. Lower = cheaper.
    """

    name = "value_ev_ebitda"
    category = "value"
    display_name = "EV / EBITDA"
    _description = "Enterprise Value to EBITDA ratio. Capital-structure-neutral valuation metric. Lower = cheaper. Center at 12x."
    source = "fundamental"
    higher_is_better = False

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        result = pd.Series(0.5, index=data.index)
        if "EV_EBITDA" in data.columns:
            ev_ebitda = data["EV_EBITDA"].astype(float)
            result = self._sigmoid(-ev_ebitda, center=-12, steepness=1/6)
        return result.clip(0, 1)

    @staticmethod
    def fetch(symbol: str) -> Optional[float]:
        """Estimate EV/EBITDA from available AKShare data.

        EV ≈ Market Cap + Total Liabilities - Cash
        This is an approximation; use terminal data for precision.
        """
        try:
            import akshare as ak
            # Get market cap and PE to derive earnings
            df = ak.stock_a_lg_indicator(symbol=symbol)
            if df is not None and not df.empty:
                pe = float(df['pe'].iloc[-1]) if 'pe' in df.columns else None
                total_mv = float(df['total_mv'].iloc[-1]) if 'total_mv' in df.columns else None
                if pe and total_mv and pe > 0:
                    earnings = total_mv / pe
                    # Rough EV: market cap (using total liabilities as debt proxy unavailable)
                    # Return None — accurate EV/EBITDA requires detailed financials
                    return None
        except Exception:
            pass
        return None
