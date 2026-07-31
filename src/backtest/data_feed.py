"""
行情数据获取模块 v2.0

支持市场:
  - A 股（akshare）: 日线/周线/月线
  - 美股（yfinance）: 日线
  - 港股（akshare）: 日线
  - 指数（沪深300、上证50、中证500等）
  - ETF

数据管理:
  - 本地 CSV 缓存（避免重复请求）
  - 批量下载关注列表
  - 数据校验 + 自动修复
  - 增量更新
"""

import pandas as pd
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

from src.backtest.symbols import normalize_market, normalize_symbol
from src.backtest.providers import CallableDataProvider, ProviderRegistry

# ---- Windows 中文编码修复 ----
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================

def resolve_data_root() -> Path:
    """Resolve cross-platform data directory.

    Priority:
      1. QUANT_DATA_DIR env var (recommended)
      2. TRADING_DATA_DIR env var (legacy)
      3. ~/.lxl_quantaxis (default)
    """
    for var in ("QUANT_DATA_DIR", "TRADING_DATA_DIR"):
        val = os.environ.get(var)
        if val:
            return Path(val)
    return Path.home() / ".lxl_quantaxis"


DATA_ROOT = str(resolve_data_root())
CACHE_DIR = os.path.join(DATA_ROOT, "cache")
INDEX_CACHE = os.path.join(CACHE_DIR, "indices")
STOCK_CACHE = os.path.join(CACHE_DIR, "stocks")

os.makedirs(INDEX_CACHE, exist_ok=True)
os.makedirs(STOCK_CACHE, exist_ok=True)

# A 股常用指数
A_INDEX_MAP = {
    "000300": "沪深300",
    "000016": "上证50",
    "000905": "中证500",
    "000852": "中证1000",
    "399001": "深证成指",
    "399006": "创业板指",
    "000688": "科创50",
}


# ============================================================
# 数据缓存层
# ============================================================

class DataCache:
    """本地 CSV 缓存，避免重复网络请求"""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir

    def _cache_path(self, symbol: str, market: str, period: str = "daily") -> str:
        filename = f"{market}_{symbol}_{period}.csv"
        return os.path.join(self.cache_dir, filename)

    def load(self, symbol: str, market: str, period: str = "daily") -> pd.DataFrame | None:
        path = self._cache_path(symbol, market, period)
        if not os.path.exists(path):
            return None
        try:
            df = pd.read_csv(path, parse_dates=["date"])
            df = df[["date", "open", "high", "low", "close", "volume"]]
            df = df.sort_values("date").reset_index(drop=True)
            # 检查数据新鲜度（超过 1 天则算过期）
            latest = df["date"].max()
            if isinstance(latest, pd.Timestamp):
                latest = latest.date()
            else:
                latest = pd.Timestamp(latest).date()
            if (datetime.now().date() - latest).days > 1:
                return None  # 过期
            return df
        except Exception:
            return None

    def save(self, df: pd.DataFrame, symbol: str, market: str, period: str = "daily"):
        path = self._cache_path(symbol, market, period)
        df.to_csv(path, index=False)

    def clear_expired(self, days: int = 30):
        """清除超过 N 天未更新的缓存"""
        cutoff = datetime.now() - timedelta(days=days)
        for f in os.listdir(self.cache_dir):
            fp = os.path.join(self.cache_dir, f)
            if os.path.isfile(fp) and f.endswith(".csv"):
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if mtime < cutoff:
                    os.remove(fp)


# 全局缓存实例
_cache = DataCache()


# ============================================================
# 数据校验
# ============================================================

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """校验并修复 OHLCV 数据"""
    required = ["date", "open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")

    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])

    # 填充缺失值
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].ffill()

    df["volume"] = df["volume"].fillna(0).astype(int)

    # 高 >= 低
    mask = df["high"] < df["low"]
    if mask.any():
        df.loc[mask, ["high", "low"]] = df.loc[mask, ["low", "high"]].values

    return df


# ============================================================
# A 股数据
# ============================================================

def _fetch_with_retry(fn, *args, max_retries=3, **kwargs):
    """带重试的数据获取"""
    import time as _time
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"    数据获取失败，{wait}s 后重试 ({attempt+1}/{max_retries})...")
                _time.sleep(wait)
    raise last_err


def get_a_stock(symbol: str, start_date: str = "2020-01-01",
                end_date: str = None, period: str = "daily",
                use_cache: bool = True) -> pd.DataFrame:
    """
    获取 A 股数据（前复权）
    period: "daily" | "weekly" | "monthly"
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # 尝试缓存
    if use_cache and period == "daily":
        cached = _cache.load(symbol, "A股", period)
        if cached is not None:
            # 检查是否覆盖请求范围
            cached_start = str(cached["date"].min())[:10]
            cached_end = str(cached["date"].max())[:10]
            if cached_start <= start_date and cached_end >= end_date:
                mask = (cached["date"] >= start_date) & (cached["date"] <= end_date)
                return cached[mask].reset_index(drop=True)

    try:
        import akshare as ak
    except ImportError:
        raise ImportError("请先安装 akshare：pip install akshare")

    df = None
    last_error = None

    # 数据源1: 新浪 (主，快且稳定)
    try:
        exchange = "sh" + symbol if symbol.startswith(("6", "9")) else "sz" + symbol
        df = ak.stock_zh_a_daily(
            symbol=exchange,
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )
    except Exception as e:
        last_error = e

    # 数据源2: 东方财富 (备选，不需要重试 — 省时间)
    if df is None or df.empty:
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, period=period,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )
        except Exception as e:
            last_error = e

    if df is None or df.empty:
        raise ValueError(f"所有数据源均失败: {symbol} | {last_error}")

    # 统一列名
    rename_map = {}
    for src, dst in [("日期", "date"), ("开盘", "open"), ("收盘", "close"),
                     ("最高", "high"), ("最低", "low"), ("成交量", "volume"),
                     ("成交额", "amount")]:
        if src in df.columns:
            rename_map[src] = dst
    if rename_map:
        df = df.rename(columns=rename_map)

    df["date"] = pd.to_datetime(df["date"])
    keep_cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep_cols]
    df = validate_data(df)

    if use_cache and period == "daily" and len(df) > 0:
        _cache.save(df, symbol, "A股", period)

    return df


# ============================================================
# 美股数据
# ============================================================

def get_us_stock(symbol: str, start_date: str = "2020-01-01",
                 end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """获取美股日线数据"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if use_cache:
        cached = _cache.load(symbol, "美股", "daily")
        if cached is not None:
            cached_start = str(cached["date"].min())[:10]
            cached_end = str(cached["date"].max())[:10]
            if cached_start <= start_date and cached_end >= end_date:
                mask = (cached["date"] >= start_date) & (cached["date"] <= end_date)
                return cached[mask].reset_index(drop=True)

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)

        if df.empty:
            raise ValueError(f"未获取到 {symbol} 的数据")

        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })

        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = validate_data(df)

        if use_cache and len(df) > 0:
            _cache.save(df, symbol, "美股", "daily")

        return df

    except ImportError:
        raise ImportError("请先安装 yfinance：pip install yfinance")


# ============================================================
# 港股数据
# ============================================================

def get_hk_stock(symbol: str, start_date: str = "2020-01-01",
                 end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """获取港股日线数据"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if use_cache:
        cached = _cache.load(symbol, "港股", "daily")
        if cached is not None:
            cached_start = str(cached["date"].min())[:10]
            cached_end = str(cached["date"].max())[:10]
            if cached_start <= start_date and cached_end >= end_date:
                mask = (cached["date"] >= start_date) & (cached["date"] <= end_date)
                return cached[mask].reset_index(drop=True)

    try:
        import akshare as ak

        df = ak.stock_hk_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )

        if df is None or df.empty:
            raise ValueError(f"未获取到港股 {symbol} 的数据")

        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
        })

        df["date"] = pd.to_datetime(df["date"])
        keep_cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep_cols]
        df = validate_data(df)

        if use_cache and len(df) > 0:
            _cache.save(df, symbol, "港股", "daily")

        return df

    except ImportError:
        raise ImportError("请先安装 akshare：pip install akshare")


# ============================================================
# 指数数据
# ============================================================

def get_index_data(symbol: str, start_date: str = "2020-01-01",
                   end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """
    获取 A 股指数日线数据
    symbol: 如 "000300"（沪深300）、"000016"（上证50）
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if use_cache:
        cached = _cache.load(symbol, "指数", "daily")
        if cached is not None:
            cached_start = str(cached["date"].min())[:10]
            cached_end = str(cached["date"].max())[:10]
            if cached_start <= start_date and cached_end >= end_date:
                mask = (cached["date"] >= start_date) & (cached["date"] <= end_date)
                return cached[mask].reset_index(drop=True)

    try:
        import akshare as ak

        df = ak.stock_zh_index_daily(symbol=f"sh{symbol}" if symbol.startswith("000") else f"sz{symbol}")
        if df is None or df.empty:
            raise ValueError(f"未获取到指数 {symbol} 的数据")

        df = df.rename(columns={
            "date": "date", "open": "open", "close": "close",
            "high": "high", "low": "low", "volume": "volume",
        })

        df["date"] = pd.to_datetime(df["date"])

        # 确保有 volume 列
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                df[col] = 0

        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = validate_data(df)

        # 过滤日期范围
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        df = df[mask]

        if use_cache and len(df) > 0:
            _cache.save(df, symbol, "指数", "daily")

        return df

    except ImportError:
        raise ImportError("请先安装 akshare：pip install akshare")


# ============================================================
# 默认 Provider 注册表
# ============================================================

# 使用 lambda 延迟解析，确保 mock patch 仍能生效
_default_registry = ProviderRegistry()
_default_registry.register(CallableDataProvider(
    name="akshare",
    market="A股",
    fetcher=lambda symbol, start_date, end_date, use_cache:
        get_a_stock(symbol, start_date=start_date, end_date=end_date, use_cache=use_cache),
))
_default_registry.register(CallableDataProvider(
    name="yfinance",
    market="美股",
    fetcher=lambda symbol, start_date, end_date, use_cache:
        get_us_stock(symbol, start_date=start_date, end_date=end_date, use_cache=use_cache),
))
_default_registry.register(CallableDataProvider(
    name="akshare",
    market="港股",
    fetcher=lambda symbol, start_date, end_date, use_cache:
        get_hk_stock(symbol, start_date=start_date, end_date=end_date, use_cache=use_cache),
))
_default_registry.register(CallableDataProvider(
    name="akshare",
    market="指数",
    fetcher=lambda symbol, start_date, end_date, use_cache:
        get_index_data(symbol, start_date=start_date, end_date=end_date, use_cache=use_cache),
))


def get_provider_registry() -> ProviderRegistry:
    """返回默认的 Provider 注册表。"""
    return _default_registry


def register_data_provider(provider, replace: bool = False) -> None:
    """注册自定义数据源到默认注册表。

    Args:
        provider: MarketDataProvider 实例
        replace:  为 True 时允许替换已有注册
    """
    _default_registry.register(provider, replace=replace)


# ============================================================
# 统一入口
# ============================================================

def get_data(symbol: str, market: str = "A股",
             start_date: str = "2020-01-01",
             end_date: str = None,
             use_cache: bool = True,
             min_lookback_days: int = 250) -> pd.DataFrame:
    """
    统一数据获取入口

    参数:
        symbol: 股票/指数代码
        market: "A股" | "美股" | "港股" | "指数"
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        use_cache: 是否使用缓存
        min_lookback_days: 最少需要多少天数据(自动扩展start_date)
    """
    # 标准化市场和代码
    market = normalize_market(market)
    symbol = normalize_symbol(symbol, market)

    # 自动扩展起始日期: 策略需要足够历史数据计算指标(如MA60需60天)
    if min_lookback_days > 0 and start_date:
        from datetime import datetime, timedelta
        try:
            target_start = datetime.strptime(start_date, "%Y-%m-%d")
            # 往前扩展，确保至少有 min_lookback_days 个日历日的数据
            extended_start = target_start - timedelta(days=min_lookback_days * 2)
            if extended_start < target_start:
                start_date = extended_start.strftime("%Y-%m-%d")
        except Exception:
            pass

    provider = _default_registry.get(market)
    return provider.fetch(symbol, start_date, end_date, use_cache=use_cache)


# ============================================================
# 批量下载
# ============================================================

def download_watchlist(watchlist: List[Dict], start_date: str = "2020-01-01",
                       verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """
    批量下载关注列表

    watchlist 格式:
        [{"symbol": "600519", "market": "A股", "name": "贵州茅台"},
         {"symbol": "000300", "market": "指数", "name": "沪深300"},
         {"symbol": "AAPL", "market": "美股", "name": "苹果"},
         {"symbol": "00700", "market": "港股", "name": "腾讯"}, ...]

    返回: {key: DataFrame}
    """
    results = {}
    errors = []
    total = len(watchlist)

    for i, item in enumerate(watchlist, 1):
        symbol = item["symbol"]
        market = item["market"]
        name = item.get("name", symbol)
        key = f"{market}:{symbol}"

        if verbose:
            print(f"  [{i}/{total}] {market} {symbol} {name} ...", end=" ")

        try:
            df = get_data(symbol, market, start_date=start_date, use_cache=True)
            results[key] = df
            if verbose:
                print(f"OK ({len(df)} 条)")
        except Exception as e:
            errors.append({"symbol": symbol, "market": market, "error": str(e)})
            if verbose:
                print(f"FAIL: {e}")

    if verbose and errors:
        print(f"\n  {len(errors)} 个失败:")
        for e in errors:
            print(f"    - {e['market']} {e['symbol']}: {e['error']}")

    return results


def get_default_watchlist() -> List[Dict]:
    """获取默认关注列表：A 股各行业龙头 + 主要指数"""
    return [
        # ---- 指数 ----
        {"symbol": "000300", "market": "指数", "name": "沪深300"},
        {"symbol": "000016", "market": "指数", "name": "上证50"},
        {"symbol": "000905", "market": "指数", "name": "中证500"},

        # ---- A 股白马 ----
        {"symbol": "600519", "market": "A股", "name": "贵州茅台"},
        {"symbol": "000858", "market": "A股", "name": "五粮液"},
        {"symbol": "601318", "market": "A股", "name": "中国平安"},
        {"symbol": "600036", "market": "A股", "name": "招商银行"},
        {"symbol": "601398", "market": "A股", "name": "工商银行"},
        {"symbol": "000333", "market": "A股", "name": "美的集团"},
        {"symbol": "600276", "market": "A股", "name": "恒瑞医药"},
        {"symbol": "300750", "market": "A股", "name": "宁德时代"},
        {"symbol": "002415", "market": "A股", "name": "海康威视"},
        {"symbol": "600900", "market": "A股", "name": "长江电力"},
        {"symbol": "601899", "market": "A股", "name": "紫金矿业"},
        {"symbol": "300059", "market": "A股", "name": "东方财富"},
        {"symbol": "688981", "market": "A股", "name": "中芯国际"},
    ]


def download_all_default(start_date: str = "2020-01-01", verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """一键下载默认关注列表全部数据"""
    watchlist = get_default_watchlist()
    return download_watchlist(watchlist, start_date=start_date, verbose=verbose)


# ============================================================
# 数据管理工具
# ============================================================

def get_data_summary() -> pd.DataFrame:
    """查看缓存数据概览"""
    rows = []
    if os.path.exists(CACHE_DIR):
        for f in sorted(os.listdir(CACHE_DIR)):
            if f.endswith(".csv"):
                path = os.path.join(CACHE_DIR, f)
                try:
                    df = pd.read_csv(path, parse_dates=["date"])
                    rows.append({
                        "文件": f,
                        "行数": len(df),
                        "起始日期": str(df["date"].min())[:10],
                        "结束日期": str(df["date"].max())[:10],
                        "大小(KB)": round(os.path.getsize(path) / 1024, 1),
                    })
                except Exception:
                    pass
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def refresh_cache(symbols: list = None):
    """强制刷新缓存"""
    if symbols is None:
        watchlist = get_default_watchlist()
    else:
        watchlist = [{"symbol": s, "market": "A股", "name": s} for s in symbols]

    print(f"刷新 {len(watchlist)} 个标的的缓存数据...")
    results = download_watchlist(watchlist, verbose=True)
    print(f"完成！成功: {len(results)}, 全部已更新到缓存。")
    return results