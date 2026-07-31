"""
Data Cache — hierarchical, market-aware local caching.

Cache path: {data_dir}/cache/{market}/{asset_type}/{symbol}/{interval}.csv

Features:
  - Auto-creates directory structure
  - Data integrity validation on load/save
  - Incremental update (merge with existing cache)
  - Deduplication and date sorting
  - Atomic file writes (write to temp, then rename)
  - Cross-market path isolation
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np

from src.data.models import Market, AssetType, CacheError


def get_data_dir() -> Path:
    """Resolve the data directory with env var priority.

    Priority:
      1. QUANT_DATA_DIR env var
      2. TRADING_DATA_DIR env var (legacy)
      3. Platform-appropriate user data directory
    """
    # 1. QUANT_DATA_DIR (new standard)
    env_dir = os.environ.get("QUANT_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    # 2. TRADING_DATA_DIR (legacy)
    env_dir = os.environ.get("TRADING_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    # 3. Platform default
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / "lxl_quantaxis" / "data"


# Global data directory
DATA_DIR = get_data_dir()
CACHE_DIR = DATA_DIR / "cache"


class DataCache:
    """Hierarchical, market-aware disk cache for OHLCV and macro data."""

    def __init__(self, cache_root: Path = None):
        self.root = Path(cache_root) if cache_root else CACHE_DIR

    # ---- Path construction ----

    def _cache_path(self, symbol: str, market: Market, asset_type: AssetType,
                    interval: str = "1d") -> Path:
        """Build hierarchical cache path.

        Example: cache/CN/STOCK/600519/1d.csv
        """
        safe_symbol = symbol.replace("/", "_").replace("\\", "_").replace(":", "_")
        return (self.root / market.value / asset_type.value /
                safe_symbol / f"{interval}.csv")

    def _legacy_path(self, symbol: str, market_str: str, period: str = "daily") -> Path:
        """Build legacy flat cache path for backward compatibility."""
        filename = f"{market_str}_{symbol}_{period}.csv"
        return self.root / filename

    # ---- Load ----

    def load(self, symbol: str, market: Market, asset_type: AssetType,
             interval: str = "1d", max_age_days: int = 1) -> Optional[pd.DataFrame]:
        """Load cached data if fresh enough.

        Args:
            max_age_days: Max age of cache before considered stale (0 = never stale).
        """
        path = self._cache_path(symbol, market, asset_type, interval)
        if not path.exists():
            return None

        try:
            df = pd.read_csv(path, parse_dates=["date"])
        except Exception as e:
            raise CacheError(f"Failed to read cache {path}: {e}")

        if df.empty:
            return None

        # Check freshness
        if max_age_days > 0 and "date" in df.columns:
            latest = pd.Timestamp(df["date"].max())
            if (datetime.now() - latest).days > max_age_days:
                return None

        return df.sort_values("date").reset_index(drop=True)

    # ---- Save ----

    def save(self, df: pd.DataFrame, symbol: str, market: Market,
             asset_type: AssetType, interval: str = "1d",
             merge: bool = False):
        """Save dataframe to cache with atomic write.

        Args:
            merge: If True, merge with existing cache data (incremental update).
        """
        if df is None or df.empty:
            return

        path = self._cache_path(symbol, market, asset_type, interval)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Deduplicate and sort
        if "date" in df.columns:
            df = df.drop_duplicates(subset=["date"]).sort_values("date")

        # Merge with existing
        if merge and path.exists():
            try:
                existing = pd.read_csv(path, parse_dates=["date"])
                df = pd.concat([existing, df], ignore_index=True)
                if "date" in df.columns:
                    df = df.drop_duplicates(subset=["date"]).sort_values("date")
            except Exception:
                pass  # If merge fails, write fresh

        # Atomic write: write to temp file, then rename
        tmp_path = path.with_suffix(".tmp")
        try:
            df.to_csv(tmp_path, index=False)
            tmp_path.replace(path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise CacheError(f"Failed to write cache {path}: {e}")

    # ---- Incremental update ----

    def update(self, df: pd.DataFrame, symbol: str, market: Market,
               asset_type: AssetType, interval: str = "1d"):
        """Incrementally update cache — merge new rows with existing."""
        return self.save(df, symbol, market, asset_type, interval, merge=True)

    # ---- Maintenance ----

    def clear_expired(self, days: int = 30):
        """Remove cache files older than N days."""
        if not self.root.exists():
            return
        cutoff = datetime.now() - timedelta(days=days)
        for path in self.root.rglob("*.csv"):
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    path.unlink()

    def exists(self, symbol: str, market: Market, asset_type: AssetType,
               interval: str = "1d") -> bool:
        """Check if cached data exists for this request."""
        return self._cache_path(symbol, market, asset_type, interval).exists()

    # ---- Legacy compatibility ----

    def load_legacy(self, symbol: str, market_str: str,
                    period: str = "daily") -> Optional[pd.DataFrame]:
        """Load from legacy flat cache format."""
        path = self._legacy_path(symbol, market_str, period)
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path, parse_dates=["date"])
            if df.empty:
                return None
            latest = pd.Timestamp(df["date"].max())
            if (datetime.now() - latest).days > 1:
                return None
            return df.sort_values("date").reset_index(drop=True)
        except Exception:
            return None

    def save_legacy(self, df: pd.DataFrame, symbol: str, market_str: str,
                    period: str = "daily"):
        """Save to legacy flat cache format. Atomic write."""
        path = self._legacy_path(symbol, market_str, period)
        path.parent.mkdir(parents=True, exist_ok=True)
        if "date" in df.columns:
            df = df.drop_duplicates(subset=["date"]).sort_values("date")
        tmp_path = path.with_suffix(".tmp")
        try:
            df.to_csv(tmp_path, index=False)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def summary(self) -> pd.DataFrame:
        """Return summary of all cached data."""
        rows = []
        if self.root.exists():
            for path in sorted(self.root.rglob("*.csv")):
                if path.is_file() and path.suffix == ".csv":
                    try:
                        df = pd.read_csv(path, parse_dates=["date"])
                        rel = path.relative_to(self.root)
                        rows.append({
                            "path": str(rel),
                            "rows": len(df),
                            "start": str(df["date"].min())[:10] if "date" in df.columns else "",
                            "end": str(df["date"].max())[:10] if "date" in df.columns else "",
                            "size_kb": round(path.stat().st_size / 1024, 1),
                        })
                    except Exception:
                        pass
        return pd.DataFrame(rows) if rows else pd.DataFrame()


# Global cache instance
cache = DataCache()
