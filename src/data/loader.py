# -*- coding: utf-8 -*-
"""
Unified Data Loader — 统一数据访问层

用 DataRepository 封装 CSV / SQLite / Parquet 读写差异。
替换原有的裸 pd.read_csv 和 sqlite3 直接调用。

集成方式:
    from src.data.loader import repo
    df = repo.load("A股_600519_daily")

架构:
    DataRepository (engine=csv|sqlite|parquet)
      ├── save(df, key) → bool
      ├── load(key)     → DataFrame | None
      └── list_keys()   → List[str]
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("data.loader")


class DataRepository:
    """统一数据仓库 — 屏蔽存储引擎差异"""

    def __init__(self, base_path: str, engine: str = "csv", **kwargs):
        self.base_path = Path(base_path)
        self.engine = engine
        self.kwargs = kwargs
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._sqlite_conn = None

    def _get_sqlite_conn(self):
        if self._sqlite_conn is None:
            db_path = (
                self.base_path / "data.db"
                if self.base_path.is_dir() else self.base_path
            )
            self._sqlite_conn = sqlite3.connect(str(db_path))
        return self._sqlite_conn

    def save(self, df: pd.DataFrame, key: str, **kwargs) -> bool:
        try:
            if self.engine == "csv":
                filepath = self.base_path / f"{key}.csv"
                df.to_csv(filepath, index=kwargs.get("index", False))
            elif self.engine == "parquet":
                filepath = self.base_path / f"{key}.parquet"
                df.to_parquet(filepath, index=kwargs.get("index", False))
            elif self.engine == "sqlite":
                conn = self._get_sqlite_conn()
                if_exists = kwargs.get("if_exists", "replace")
                df.to_sql(key, conn, if_exists=if_exists,
                          index=kwargs.get("index", False))
            else:
                raise ValueError(f"不支持的引擎: {self.engine}")
            return True
        except Exception as e:
            logger.error(f"保存失败 [{key}]: {e}")
            return False

    def load(self, key: str, **kwargs) -> Optional[pd.DataFrame]:
        try:
            if self.engine == "csv":
                filepath = self.base_path / f"{key}.csv"
                if not filepath.exists():
                    return None
                return pd.read_csv(
                    filepath,
                    index_col=kwargs.get("index_col", 0),
                    parse_dates=kwargs.get("parse_dates", True),
                )
            elif self.engine == "parquet":
                filepath = self.base_path / f"{key}.parquet"
                if not filepath.exists():
                    return None
                return pd.read_parquet(filepath)
            elif self.engine == "sqlite":
                conn = self._get_sqlite_conn()
                sql = kwargs.get("sql", f"SELECT * FROM {key}")
                return pd.read_sql(sql, conn, index_col=kwargs.get("index_col", None))
            else:
                raise ValueError(f"不支持的引擎: {self.engine}")
        except Exception as e:
            logger.error(f"加载失败 [{key}]: {e}")
            return None

    def list_keys(self) -> List[str]:
        if self.engine == "csv":
            return sorted([f.stem for f in self.base_path.glob("*.csv")])
        elif self.engine == "parquet":
            return sorted([f.stem for f in self.base_path.glob("*.parquet")])
        elif self.engine == "sqlite":
            conn = self._get_sqlite_conn()
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return sorted([r[0] for r in cur.fetchall()])
        return []

    def close(self):
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None


# ═══════════════════════════════════════════
# 全局单例 — 替代裸 pd.read_csv
# ═══════════════════════════════════════════

DATA_DIR = os.environ.get(
    "QUANT_DATA_DIR",
    os.environ.get("TRADING_DATA_DIR", "D:/trading_data"),
)

# 行情缓存 (CSV)
cache_repo = DataRepository(os.path.join(DATA_DIR, "cache"), engine="csv")

# 结构化数据 (SQLite)
db_repo = DataRepository(DATA_DIR, engine="sqlite")


# ── 便捷加载函数: 兼容旧 data_feed 接口 ──

def load_ohlcv(symbol: str, market: str = "A股") -> Optional[pd.DataFrame]:
    """从统一仓库加载 OHLCV 数据 (兼容旧接口)"""
    key = f"{market}_{symbol}_daily"
    df = cache_repo.load(key)
    if df is not None:
        return df
    # 回退: 尝试 MarketDB
    from src.data.market_db import market_db
    return market_db.get_kline(symbol, market)


def save_ohlcv(symbol: str, market: str, df: pd.DataFrame):
    """保存 OHLCV 数据到统一仓库"""
    key = f"{market}_{symbol}_daily"
    cache_repo.save(df, key, index=False)


def list_cached_symbols(market: str = "A股") -> List[str]:
    """列出已缓存的所有标的"""
    prefix = f"{market}_"
    keys = cache_repo.list_keys()
    return [
        k[len(prefix):].replace("_daily", "")
        for k in keys if k.startswith(prefix) and k.endswith("_daily")
    ]
