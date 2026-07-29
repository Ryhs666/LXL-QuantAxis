"""
MarketDataAdapter — 多市场统一数据适配器 (v6.2)

接口: get_price(symbol, start, end)
  .SH / .SZ → A股 (akshare)
  .HK       → 港股 (yfinance)
  .US       → 美股 (yfinance)
  .CSI      → A股指数 (akshare)

输出: 标准 OHLCV DataFrame (date, open, high, low, close, volume)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


class MarketDataAdapter:
    """多市场数据适配器"""

    def __init__(self):
        self._cache = {}

    def get_price(self, symbol: str, start: str = "2020-01-01",
                  end: str = None, use_cache: bool = True) -> pd.DataFrame:
        """
        统一数据获取接口

        参数:
          symbol: 股票代码 (如 600498.SH, 000858.SZ, 0700.HK, AAPL.US, 000300.CSI)
          start:  起始日期 YYYY-MM-DD
          end:    截止日期 (默认今天)
          use_cache: 是否使用本地缓存

        返回:
          DataFrame with columns: date, open, high, low, close, volume
        """
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        # 解析市场
        market, raw_symbol = self._parse_symbol(symbol)

        # 缓存检查
        cache_key = f"{market}_{raw_symbol}_{start}_{end}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # 按市场分发
        if market == "A":
            df = self._get_a_stock(raw_symbol, start, end, use_cache)
        elif market == "HK":
            df = self._get_hk_stock(raw_symbol, start, end)
        elif market == "US":
            df = self._get_us_stock(raw_symbol, start, end)
        elif market == "CSI":
            df = self._get_index(raw_symbol, start, end, use_cache)
        else:
            raise ValueError(f"不支持的市场: {market} (symbol={symbol})")

        # 统一格式
        if df is not None and len(df) > 0:
            df = self._normalize(df, raw_symbol)

        # 缓存
        if use_cache and df is not None and len(df) > 0:
            self._cache[cache_key] = df.copy()

        return df

    # ═══════════════════════════════════════════
    # 符号解析
    # ═══════════════════════════════════════════

    @staticmethod
    def _parse_symbol(symbol: str) -> tuple:
        """解析股票代码 → (market, raw_symbol)"""
        s = symbol.strip().upper()

        if s.endswith(".SH") or s.endswith(".SZ"):
            return "A", s.replace(".SH", "").replace(".SZ", "")
        elif s.endswith(".HK"):
            hk_code = s.replace(".HK", "").lstrip("0")
            if len(hk_code) < 4:
                hk_code = hk_code.zfill(4)
            return "HK", hk_code + ".HK"
        elif s.endswith(".US"):
            return "US", s.replace(".US", "")
        elif s.endswith(".CSI"):
            return "CSI", s.replace(".CSI", "")
        # 无后缀判断
        elif s.startswith("6") and len(s) == 6:
            return "A", s  # 上海
        elif (s.startswith("0") or s.startswith("3")) and len(s) == 6:
            return "A", s  # 深圳
        elif s.isdigit() and len(s) <= 5:
            return "HK", s.zfill(4) + ".HK"  # 港股
        else:
            return "US", s  # 美股

    # ═══════════════════════════════════════════
    # A股 (akshare)
    # ═══════════════════════════════════════════

    def _get_a_stock(self, symbol: str, start: str, end: str,
                     use_cache: bool = True) -> Optional[pd.DataFrame]:
        """A股数据"""
        try:
            from src.backtest.data_feed import get_data
            return get_data(symbol, "A股", start_date=start,
                          end_date=end, use_cache=use_cache)
        except Exception as e:
            print(f"[MarketAdapter] A股 {symbol} 获取失败: {e}")
            return None

    def _get_index(self, symbol: str, start: str, end: str,
                   use_cache: bool = True) -> Optional[pd.DataFrame]:
        """A股指数"""
        try:
            from src.backtest.data_feed import get_index_data
            return get_index_data(symbol, start, end, use_cache=use_cache)
        except Exception as e:
            print(f"[MarketAdapter] 指数 {symbol} 获取失败: {e}")
            return None

    # ═══════════════════════════════════════════
    # 港股/美股 (yfinance)
    # ═══════════════════════════════════════════

    @staticmethod
    def _get_hk_stock(symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """港股 (yfinance)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)
            if df is None or df.empty:
                return None
            df = df.reset_index()
            df.rename(columns={
                "Date": "date", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume"
            }, inplace=True)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            return df[["date", "open", "high", "low", "close", "volume"]]
        except ImportError:
            print("[MarketAdapter] 请安装 yfinance: pip install yfinance")
            return None
        except Exception as e:
            print(f"[MarketAdapter] 港股 {symbol} 获取失败: {e}")
            return None

    @staticmethod
    def _get_us_stock(symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """美股 (yfinance)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)
            if df is None or df.empty:
                return None
            df = df.reset_index()
            df.rename(columns={
                "Date": "date", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume"
            }, inplace=True)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            return df[["date", "open", "high", "low", "close", "volume"]]
        except ImportError:
            print("[MarketAdapter] 请安装 yfinance: pip install yfinance")
            return None
        except Exception as e:
            print(f"[MarketAdapter] 美股 {symbol} 获取失败: {e}")
            return None

    # ═══════════════════════════════════════════
    # 格式统一
    # ═══════════════════════════════════════════

    @staticmethod
    def _normalize(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """统一 OHLCV 格式"""
        # 确保列名小写
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl in ("date", "open", "high", "low", "close", "volume"):
                col_map[col] = cl
            elif cl == "datetime":
                col_map[col] = "date"
        if col_map:
            df = df.rename(columns=col_map)

        # 确保有必需列
        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            for c in missing:
                if c == "volume":
                    df[c] = 0
                elif c in ("open", "high", "low"):
                    df[c] = df.get("close", 0)

        cols = [c for c in required if c in df.columns]
        df = df[cols].copy()

        # 去重排序
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

        # 填充缺失值
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = df[col].ffill().replace(0, np.nan).ffill()

        return df

    # ═══════════════════════════════════════════
    # 批量
    # ═══════════════════════════════════════════

    def get_multi(self, symbols: list, start: str = "2020-01-01",
                  end: str = None) -> dict:
        """批量获取 → {symbol: DataFrame}"""
        results = {}
        for sym in symbols:
            try:
                df = self.get_price(sym, start, end)
                if df is not None and len(df) > 0:
                    results[sym] = df
            except Exception as e:
                print(f"[MarketAdapter] {sym} 失败: {e}")
        return results


# 全局实例
adapter = MarketDataAdapter()


def get_price(symbol: str, start: str = "2020-01-01",
              end: str = None) -> pd.DataFrame:
    """快捷函数"""
    return adapter.get_price(symbol, start, end)
