"""
统一数据源接口 v1.0

提供:
  - MarketDataProvider:  抽象基类，定义数据源的统一接口
  - CallableDataProvider: 将现有函数包装为统一 Provider
  - ProviderRegistry:     数据源注册表，支持按市场获取/替换
"""

from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from src.backtest.symbols import normalize_market


# ============================================================
# 抽象基类
# ============================================================

class MarketDataProvider(ABC):
    """市场数据源的统一抽象接口。

    子类必须实现 name、market 属性和 fetch() 方法。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称，如 'akshare'、'yfinance'。"""
        ...

    @property
    @abstractmethod
    def market(self) -> str:
        """标准化市场名称：'A股' | '美股' | '港股' | '指数'。"""
        ...

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        start_date: str,
        end_date: str | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取 OHLCV 数据。

        Args:
            symbol:     标准化后的证券代码
            start_date: 起始日期 YYYY-MM-DD
            end_date:   结束日期 YYYY-MM-DD（None 表示今天）
            use_cache:  是否使用本地缓存

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        ...


# ============================================================
# 可调用适配器
# ============================================================

class CallableDataProvider(MarketDataProvider):
    """将任意可调用对象包装为 MarketDataProvider。

    用于接入现有数据获取函数（如 get_a_stock、get_us_stock 等），
    无需修改这些函数的内部实现。
    """

    def __init__(self, name: str, market: str, fetcher):
        """构造适配器。

        Args:
            name:    数据源名称
            market:  市场（会自动标准化）
            fetcher: 可调用对象，签名为 (symbol, start_date, end_date, use_cache) -> DataFrame
        """
        self._name = name
        self._market = normalize_market(market)
        if not callable(fetcher):
            raise TypeError(f"fetcher 必须是可调用对象，收到: {type(fetcher).__name__}")
        self._fetcher = fetcher

    @property
    def name(self) -> str:
        return self._name

    @property
    def market(self) -> str:
        return self._market

    def fetch(
        self,
        symbol: str,
        start_date: str,
        end_date: str | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """委托给内部的 fetcher 可调用对象。"""
        return self._fetcher(
            symbol,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )


# ============================================================
# 注册表
# ============================================================

class ProviderRegistry:
    """市场数据源注册表。

    每个市场最多注册一个 Provider。同一市场重复注册默认抛出 ValueError，
    设置 replace=True 可强制替换。
    """

    def __init__(self):
        self._providers: dict[str, MarketDataProvider] = {}

    def register(self, provider: MarketDataProvider, replace: bool = False) -> None:
        """注册数据源。

        Args:
            provider: MarketDataProvider 实例
            replace:  为 True 时允许替换已有注册

        Raises:
            TypeError:  provider 不是 MarketDataProvider 实例
            ValueError: 同一市场已注册且 replace=False
        """
        if not isinstance(provider, MarketDataProvider):
            raise TypeError(
                f"provider 必须是 MarketDataProvider 实例，收到: {type(provider).__name__}"
            )
        market = provider.market  # 已在构造时标准化
        if market in self._providers and not replace:
            existing = self._providers[market]
            raise ValueError(
                f"市场 {market!r} 已注册 Provider '{existing.name}'，"
                f"使用 replace=True 可强制替换"
            )
        self._providers[market] = provider

    def get(self, market: str) -> MarketDataProvider:
        """按市场获取 Provider。

        支持所有市场别名（A股/CN/A, 美股/US/USA, 港股/HK/HONGKONG, 指数/INDEX/IDX）。

        Raises:
            ValueError: 市场未注册
        """
        market = normalize_market(market)
        if market not in self._providers:
            raise ValueError(
                f"市场 {market!r} 未注册 Provider，"
                f"已注册: {self.markets()}"
            )
        return self._providers[market]

    def markets(self) -> List[str]:
        """返回已注册的标准市场名称列表，顺序稳定。"""
        return list(self._providers.keys())
