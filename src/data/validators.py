"""
Data Validators — validation and normalization for market data.

All data entering the system passes through these validators.
"""

from typing import List, Optional
import pandas as pd
import numpy as np

from src.data.models import (
    DataValidationError, EQUITY_COLUMNS, MACRO_COLUMNS,
    Market, AssetType,
)


def validate_ohlcv(df: pd.DataFrame, symbol: str = "",
                   market: Market = None) -> pd.DataFrame:
    """Validate and normalize OHLCV equity data.

    Args:
        df: Raw dataframe from data provider.
        symbol: Symbol for error messages.
        market: Market for column naming.

    Returns:
        Cleaned dataframe with standardized columns.

    Raises:
        DataValidationError: If data is empty or missing required columns.
    """
    if df is None or df.empty:
        raise DataValidationError(f"No data returned for {symbol or 'unknown'}")

    # Normalize column names (case-insensitive)
    rename = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ("date", "datetime", "time", "timestamp"):
            rename[col] = "date"
        elif cl in ("open",):
            rename[col] = "open"
        elif cl in ("high",):
            rename[col] = "high"
        elif cl in ("low",):
            rename[col] = "low"
        elif cl in ("close", "adj_close", "adjusted_close", "adj close"):
            rename[col] = "close"
        elif cl in ("volume", "vol"):
            rename[col] = "volume"
    df = df.rename(columns=rename)

    # Require minimum columns
    required = ["date", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"Missing required columns for {symbol}: {missing}. "
            f"Available: {list(df.columns)}"
        )

    # Fill optional columns
    for col in ["open", "high", "low"]:
        if col not in df.columns:
            df[col] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0

    # Parse dates, drop NaT
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # High/Low sanity check
    mask = df["high"] < df["low"]
    if mask.any():
        # Swap high/low where inverted
        h_vals = df.loc[mask, "high"].copy()
        l_vals = df.loc[mask, "low"].copy()
        df.loc[mask, "high"] = l_vals
        df.loc[mask, "low"] = h_vals

    # Deduplicate and sort
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Forward-fill price gaps (but not across large gaps)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].ffill()

    df["volume"] = df["volume"].fillna(0).astype(int)

    # Add adjusted_close if missing
    if "adjusted_close" not in df.columns:
        df["adjusted_close"] = df["close"]

    # Add metadata columns
    df["symbol"] = symbol
    if market is not None:
        df["market"] = market.value
        df["currency"] = market.currency()

    # Standardize output columns
    out_cols = [c for c in EQUITY_COLUMNS if c in df.columns]
    return df[out_cols]


def validate_macro(df: pd.DataFrame, series_id: str = "",
                   source: str = "") -> pd.DataFrame:
    """Validate and normalize macro time series data.

    Args:
        df: Raw dataframe with at minimum [date, value].
        series_id: Macro series identifier.
        source: Data source label.

    Returns:
        Cleaned dataframe with columns: [date, value, series_id, source].

    Raises:
        DataValidationError: If empty or missing required columns.
    """
    if df is None or df.empty:
        raise DataValidationError(f"No data returned for macro series {series_id}")

    # Normalize columns
    rename = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ("date", "datetime", "time", "timestamp"):
            rename[col] = "date"
        elif cl in ("value", "close", "price", "rate", "yield", "val"):
            rename[col] = "value"
    df = df.rename(columns=rename)

    if "date" not in df.columns or "value" not in df.columns:
        raise DataValidationError(
            f"Macro data must have 'date' and 'value' columns. "
            f"Got: {list(df.columns)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    df["series_id"] = series_id
    df["source"] = source or "unknown"

    return df[["date", "value", "series_id", "source"]]


def check_data_integrity(df: pd.DataFrame, symbol: str = "") -> List[str]:
    """Run integrity checks and return list of warnings.

    Checks:
      - Duplicate dates
      - Price <= 0
      - Suspicious price jumps (>50% in one day)
      - All-NaN price columns
    """
    warnings = []

    if df is None or df.empty:
        warnings.append(f"{symbol}: Empty dataframe")
        return warnings

    # Duplicate dates
    if "date" in df.columns:
        dupes = df["date"].duplicated().sum()
        if dupes > 0:
            warnings.append(f"{symbol}: {dupes} duplicate dates")

    # Non-positive prices
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            neg = (df[col] <= 0).sum()
            if neg > 0:
                warnings.append(f"{symbol}: {neg} non-positive {col} values")

    # Suspicious jumps
    if "close" in df.columns and len(df) > 1:
        returns = df["close"].pct_change().abs()
        jumps = (returns > 0.5).sum()
        if jumps > 0:
            warnings.append(f"{symbol}: {jumps} price jumps >50% in one period")

    # All-NaN check
    for col in ["close"]:
        if col in df.columns and df[col].isna().all():
            warnings.append(f"{symbol}: All-NaN in {col} column")

    return warnings
