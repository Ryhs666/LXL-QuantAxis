"""
市场元数据与基础交易日历 v1.0

提供:
  - MarketMetadata:    不可变数据类，描述市场时区/币种/日历
  - MarketCalendar:    基础交易日判断（周一至周五，可注入假日）
  - get_market_metadata:  按市场获取元数据
  - get_market_timezone:  按市场获取 zoneinfo.ZoneInfo
  - get_market_calendar:  按市场获取 MarketCalendar
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Union, Set
import zoneinfo

from src.backtest.symbols import normalize_market


# ============================================================
# MarketMetadata
# ============================================================

@dataclass(frozen=True)
class MarketMetadata:
    """不可变市场元数据。

    Attributes:
        market:   标准化市场名称
        timezone: IANA 时区标识符
        currency: ISO 4217 货币代码
        calendar: 日历标识符
    """
    market: str
    timezone: str
    currency: str
    calendar: str


# 四个市场定义
_METADATA: dict[str, MarketMetadata] = {
    "A股": MarketMetadata(
        market="A股",
        timezone="Asia/Shanghai",
        currency="CNY",
        calendar="CN",
    ),
    "美股": MarketMetadata(
        market="美股",
        timezone="America/New_York",
        currency="USD",
        calendar="US",
    ),
    "港股": MarketMetadata(
        market="港股",
        timezone="Asia/Hong_Kong",
        currency="HKD",
        calendar="HK",
    ),
    "指数": MarketMetadata(
        market="指数",
        timezone="Asia/Shanghai",
        currency="CNY",
        calendar="CN_INDEX",
    ),
}


def get_market_metadata(market: str) -> MarketMetadata:
    """获取市场元数据。

    支持所有市场别名（A股/CN/A, 美股/US/USA, 港股/HK/HONGKONG, 指数/INDEX/IDX）。

    Raises:
        ValueError: 未知市场
    """
    market = normalize_market(market)
    return _METADATA[market]


def get_market_timezone(market: str) -> zoneinfo.ZoneInfo:
    """获取市场时区（仅使用标准库 zoneinfo）。

    Raises:
        ValueError: 未知市场
        zoneinfo.ZoneInfoNotFoundError: 无效时区标识符
    """
    meta = get_market_metadata(market)
    return zoneinfo.ZoneInfo(meta.timezone)


# ============================================================
# MarketCalendar
# ============================================================

def _to_date(value: Union[date, datetime, str]) -> date:
    """将 date / datetime / YYYY-MM-DD 字符串统一转换为 date。"""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"日期字符串格式必须为 YYYY-MM-DD: {value!r}")
    raise TypeError(f"不支持的类型: {type(value).__name__}")


class MarketCalendar:
    """基础交易日历。

    规则:
      - 周一至周五为基础交易日
      - 周六、周日不是交易日
      - 额外注入的 holidays 中的日期不是交易日

    注意: 这是基础框架，不包含完整官方节假日。用户可通过 holidays 参数注入。
    """

    def __init__(self, market: str, holidays: Optional[Union[Set, list, tuple]] = None):
        self._market = normalize_market(market)
        self._holidays: Set[date] = set()
        if holidays:
            for h in holidays:
                self._holidays.add(_to_date(h))

    @property
    def market(self) -> str:
        return self._market

    def is_trading_day(self, value: Union[date, datetime, str]) -> bool:
        """判断是否为交易日。

        周一至周五且不在 holidays 中为交易日，否则不是。
        """
        d = _to_date(value)
        if d.weekday() >= 5:  # 周六(5) 或 周日(6)
            return False
        if d in self._holidays:
            return False
        return True

    def next_trading_day(self, value: Union[date, datetime, str]) -> date:
        """返回输入日期之后的下一个交易日（不含输入当天）。"""
        d = _to_date(value) + timedelta(days=1)
        while not self.is_trading_day(d):
            d += timedelta(days=1)
        return d

    def previous_trading_day(self, value: Union[date, datetime, str]) -> date:
        """返回输入日期之前的上一个交易日（不含输入当天）。"""
        d = _to_date(value) - timedelta(days=1)
        while not self.is_trading_day(d):
            d -= timedelta(days=1)
        return d


def get_market_calendar(
    market: str,
    holidays: Optional[Union[Set, list, tuple]] = None,
) -> MarketCalendar:
    """获取市场交易日历。

    Args:
        market:   市场名称（支持别名）
        holidays: 额外非交易日集合（date / datetime / YYYY-MM-DD 字符串）

    注意: 这是基础框架，不包含完整官方节假日。
    """
    return MarketCalendar(market, holidays=holidays)
