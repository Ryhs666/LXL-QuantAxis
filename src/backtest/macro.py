"""
标准化宏观数据合约 v1.0

提供:
  - MacroSeriesMetadata:   宏观指标元数据（不可变 dataclass）
  - normalize_macro_frame: 将任意宏观 DataFrame 转为标准格式
  - MacroDataProvider:     宏观数据源抽象基类
  - CallableMacroProvider:  将可调用对象包装为 Provider
  - MacroProviderRegistry:  Provider 注册表
  - get_macro_data:        统一宏观数据获取入口

本次不连接真实宏观数据 API。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# ============================================================
# 宏观指标元数据
# ============================================================

@dataclass(frozen=True)
class MacroSeriesMetadata:
    """不可变宏观指标元数据。

    Attributes:
        code:      指标代码（大写）
        name:      指标中文/英文名称
        region:    地区代码（CN / US）
        frequency: 数据频率（monthly / daily）
        unit:      单位（percent / index）
    """
    code: str
    name: str
    region: str
    frequency: str
    unit: str


# 预置指标
_PRESET_SERIES: Dict[str, MacroSeriesMetadata] = {
    "CN_CPI_YOY": MacroSeriesMetadata(
        code="CN_CPI_YOY",
        name="中国CPI同比",
        region="CN",
        frequency="monthly",
        unit="percent",
    ),
    "CN_PPI_YOY": MacroSeriesMetadata(
        code="CN_PPI_YOY",
        name="中国PPI同比",
        region="CN",
        frequency="monthly",
        unit="percent",
    ),
    "CN_PMI": MacroSeriesMetadata(
        code="CN_PMI",
        name="中国制造业PMI",
        region="CN",
        frequency="monthly",
        unit="index",
    ),
    "CN_LPR_1Y": MacroSeriesMetadata(
        code="CN_LPR_1Y",
        name="中国1年期LPR",
        region="CN",
        frequency="monthly",
        unit="percent",
    ),
    "US_CPI_YOY": MacroSeriesMetadata(
        code="US_CPI_YOY",
        name="美国CPI同比",
        region="US",
        frequency="monthly",
        unit="percent",
    ),
    "US_FED_FUNDS": MacroSeriesMetadata(
        code="US_FED_FUNDS",
        name="美国联邦基金利率",
        region="US",
        frequency="monthly",
        unit="percent",
    ),
    "US_UNEMPLOYMENT": MacroSeriesMetadata(
        code="US_UNEMPLOYMENT",
        name="美国失业率",
        region="US",
        frequency="monthly",
        unit="percent",
    ),
    "US_10Y_YIELD": MacroSeriesMetadata(
        code="US_10Y_YIELD",
        name="美国10年期国债收益率",
        region="US",
        frequency="daily",
        unit="percent",
    ),
}


def normalize_macro_code(code: str) -> str:
    """标准化宏观指标代码。

    规则: 清除首尾空格，转为大写。

    Raises:
        ValueError: code 为 None、空字符串或未知代码。
    """
    if code is None:
        raise ValueError("macro code 不能为 None")
    if not isinstance(code, str):
        raise ValueError(f"macro code 必须是字符串，收到: {type(code).__name__}")
    cleaned = code.strip().upper()
    if not cleaned:
        raise ValueError("macro code 不能为空字符串")
    if cleaned not in _PRESET_SERIES:
        raise ValueError(
            f"未知宏观指标代码: {code!r}，可用: {list_macro_series()}"
        )
    return cleaned


def get_macro_metadata(code: str) -> MacroSeriesMetadata:
    """获取宏观指标元数据。

    Raises:
        ValueError: 未知代码。
    """
    code = normalize_macro_code(code)
    return _PRESET_SERIES[code]


def list_macro_series(region: str | None = None) -> List[str]:
    """列出宏观指标代码，可按地区筛选。

    Args:
        region: CN / US（忽略大小写和空格），None 返回全部。

    Raises:
        ValueError: region 非法。
    """
    if region is None:
        return list(_PRESET_SERIES.keys())

    if not isinstance(region, str):
        raise ValueError(f"region 必须是字符串，收到: {type(region).__name__}")

    region = region.strip().upper()
    if not region:
        raise ValueError("region 不能为空字符串")
    if region not in ("CN", "US"):
        raise ValueError(f"未知 region: {region!r}，可选: CN, US")

    return [c for c, m in _PRESET_SERIES.items() if m.region == region]


# ============================================================
# 标准宏观数据格式
# ============================================================

def normalize_macro_frame(
    df: pd.DataFrame,
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """将宏观数据 DataFrame 转换为标准格式。

    标准格式: date + value 两列，按 date 升序。

    Args:
        df:         原始 DataFrame（不修改）
        code:       宏观指标代码
        start_date: YYYY-MM-DD 开始日期过滤
        end_date:   YYYY-MM-DD 结束日期过滤

    Returns:
        标准格式 DataFrame，attrs 包含元数据。

    Raises:
        ValueError: 列缺失、value 无法转换、日期区间非法。
    """
    # 校验日期区间
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date}) 不能晚于 end_date ({end_date})"
            )

    code = normalize_macro_code(code)

    # 不修改输入
    df = df.copy()

    # 列校验
    if "date" not in df.columns:
        raise ValueError(f"DataFrame 缺少 'date' 列，现有列: {list(df.columns)}")
    if "value" not in df.columns:
        raise ValueError(f"DataFrame 缺少 'value' 列，现有列: {list(df.columns)}")

    # 只保留需要的列
    df = df[["date", "value"]].copy()

    # date 转 datetime
    df["date"] = pd.to_datetime(df["date"])

    # value 转数值
    try:
        df["value"] = pd.to_numeric(df["value"])
    except (ValueError, TypeError) as e:
        raise ValueError(f"value 列存在无法转换为数值的数据: {e}")

    # 去重（保留最后一条）
    df = df.drop_duplicates(subset=["date"], keep="last")

    # 按 date 升序
    df = df.sort_values("date").reset_index(drop=True)

    # 日期过滤
    if start_date is not None:
        mask = df["date"] >= pd.Timestamp(start_date)
        df = df.loc[mask]
    if end_date is not None:
        mask = df["date"] <= pd.Timestamp(end_date)
        df = df.loc[mask]

    # 重新索引
    df = df.reset_index(drop=True)

    # 附加元数据
    meta = get_macro_metadata(code)
    df.attrs["code"] = meta.code
    df.attrs["name"] = meta.name
    df.attrs["region"] = meta.region
    df.attrs["frequency"] = meta.frequency
    df.attrs["unit"] = meta.unit

    return df


# ============================================================
# 宏观 Provider 接口
# ============================================================

class MacroDataProvider(ABC):
    """宏观数据源抽象基类。

    子类必须实现 name 属性和 fetch() 方法。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称。"""
        ...

    @abstractmethod
    def fetch(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """获取宏观数据。

        Args:
            code:       宏观指标代码
            start_date: 开始日期 YYYY-MM-DD
            end_date:   结束日期 YYYY-MM-DD

        Returns:
            原始 DataFrame（由调用方用 normalize_macro_frame 标准化）。
        """
        ...


class CallableMacroProvider(MacroDataProvider):
    """将可调用对象包装为 MacroDataProvider。"""

    def __init__(self, name: str, fetcher):
        if not name or not name.strip():
            raise ValueError("Provider 名称不能为空")
        self._name = name.strip()
        if not callable(fetcher):
            raise TypeError(f"fetcher 必须是可调用对象，收到: {type(fetcher).__name__}")
        self._fetcher = fetcher

    @property
    def name(self) -> str:
        return self._name

    def fetch(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        return self._fetcher(code, start_date=start_date, end_date=end_date)


# ============================================================
# 宏观 Provider 注册表
# ============================================================

class MacroProviderRegistry:
    """宏观数据源注册表。

    每个名称最多注册一个 Provider。
    """

    def __init__(self):
        self._providers: Dict[str, MacroDataProvider] = {}

    def register(self, provider: MacroDataProvider, replace: bool = False) -> None:
        """注册 Provider。

        名称自动清除首尾空格并转为小写。

        Raises:
            TypeError:  provider 不是 MacroDataProvider
            ValueError: 名称为空或重复注册
        """
        if not isinstance(provider, MacroDataProvider):
            raise TypeError(
                f"provider 必须是 MacroDataProvider 实例，收到: {type(provider).__name__}"
            )
        key = provider.name.strip().lower()
        if not key:
            raise ValueError("Provider 名称不能为空")
        if key in self._providers and not replace:
            raise ValueError(
                f"Provider '{key}' 已注册，使用 replace=True 可强制替换"
            )
        self._providers[key] = provider

    def get(self, name: str) -> MacroDataProvider:
        """按名称获取 Provider。

        Raises:
            ValueError: 未注册的名称。
        """
        key = name.strip().lower()
        if not key:
            raise ValueError("Provider 名称不能为空")
        if key not in self._providers:
            raise ValueError(
                f"Provider '{key}' 未注册，已注册: {self.names()}"
            )
        return self._providers[key]

    def names(self) -> List[str]:
        """返回已注册的 Provider 名称列表，顺序稳定。"""
        return [p.name for p in self._providers.values()]


# ============================================================
# 统一调用入口
# ============================================================

def get_macro_data(
    code: str,
    provider: MacroDataProvider,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """统一宏观数据获取入口。

    执行顺序:
      1. 标准化 code
      2. 调用 provider.fetch()
      3. 使用 normalize_macro_frame() 标准化
      4. 返回标准 DataFrame

    Args:
        code:       宏观指标代码
        provider:   MacroDataProvider 实例
        start_date: 开始日期 YYYY-MM-DD
        end_date:   结束日期 YYYY-MM-DD

    Raises:
        TypeError:  provider 不是 MacroDataProvider
        ValueError: code 非法、数据格式非法
    """
    if not isinstance(provider, MacroDataProvider):
        raise TypeError(
            f"provider 必须是 MacroDataProvider 实例，收到: {type(provider).__name__}"
        )
    code = normalize_macro_code(code)
    raw = provider.fetch(code, start_date=start_date, end_date=end_date)
    return normalize_macro_frame(raw, code, start_date=start_date, end_date=end_date)
