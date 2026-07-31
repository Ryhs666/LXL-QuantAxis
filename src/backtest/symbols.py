"""
市场和证券代码标准化模块

提供:
  - normalize_market: 统一市场名称
  - normalize_symbol: 统一证券代码格式
  - instrument_key:  生成标准化标的键
"""

import re

# ============================================================
# 市场名称标准化
# ============================================================

_MARKET_ALIASES = {
    "A股": "A股",
    "A": "A股",
    "CN": "A股",
    "CHINA": "A股",
    "美股": "美股",
    "US": "美股",
    "USA": "美股",
    "港股": "港股",
    "HK": "港股",
    "HONGKONG": "港股",
    "指数": "指数",
    "INDEX": "指数",
    "IDX": "指数",
}


def normalize_market(market: str) -> str:
    """统一市场名称。

    支持的别名（英文忽略大小写，自动清理首尾空格）:

        A股:  A股, A, CN, CHINA
        美股:  美股, US, USA
        港股:  港股, HK, HONGKONG
        指数:  指数, INDEX, IDX

    Raises:
        ValueError: market 为 None、空字符串或未知市场。
    """
    if market is None:
        raise ValueError("market 不能为 None")
    if not isinstance(market, str):
        raise ValueError(f"market 必须是字符串，收到: {type(market).__name__}")
    cleaned = market.strip()
    if not cleaned:
        raise ValueError("market 不能为空字符串")
    key = cleaned.upper()
    if key not in _MARKET_ALIASES:
        raise ValueError(f"未知市场: {market!r}，可选: A股/A/CN/CHINA, 美股/US/USA, 港股/HK/HONGKONG, 指数/INDEX/IDX")
    return _MARKET_ALIASES[key]


# ============================================================
# 证券代码标准化
# ============================================================

def normalize_symbol(symbol: str, market: str) -> str:
    """统一证券代码格式。

    Raises:
        ValueError: symbol 为 None、空字符串或包含非法字符。
    """
    if symbol is None:
        raise ValueError("symbol 不能为 None")
    if not isinstance(symbol, str):
        raise ValueError(f"symbol 必须是字符串，收到: {type(symbol).__name__}")
    s = symbol.strip()
    if not s:
        raise ValueError("symbol 不能为空字符串")

    # 先标准化 market，确保分发正确
    market = normalize_market(market)

    if market == "A股":
        return _normalize_a_stock(s)
    elif market == "指数":
        return _normalize_index(s)
    elif market == "港股":
        return _normalize_hk_stock(s)
    elif market == "美股":
        return _normalize_us_stock(s)
    else:
        raise ValueError(f"未知市场: {market!r}")


def _normalize_a_stock(s: str) -> str:
    """A股: 去掉 sh/sz 前缀和分隔符，保留6位数字。"""
    s = s.upper()
    # 去掉 exchange. 前缀 (如 sh.600519, SZ.000001)
    s = re.sub(r'^(SH|SZ)\.', '', s)
    # 去掉裸 exchange 前缀 (如 sh600519, sz000001)
    s = re.sub(r'^(SH|SZ)(?=\d)', '', s)
    if not re.match(r'^\d{6}$', s):
        raise ValueError(f"A股代码必须是6位数字: {s!r}")
    return s


def _normalize_index(s: str) -> str:
    """指数: 去掉 sh/sz 前缀和分隔符，保留6位数字。"""
    s = s.upper()
    s = re.sub(r'^(SH|SZ)\.', '', s)
    s = re.sub(r'^(SH|SZ)(?=\d)', '', s)
    if not re.match(r'^\d{6}$', s):
        raise ValueError(f"指数代码必须是6位数字: {s!r}")
    return s


def _normalize_hk_stock(s: str) -> str:
    """港股: 去掉 .HK 后缀，补齐为5位数字。"""
    s = s.upper()
    # 去掉 .HK 后缀
    s = re.sub(r'\.HK$', '', s)
    if not re.match(r'^\d{1,5}$', s):
        raise ValueError(f"港股代码必须是1-5位数字: {s!r}")
    # 补齐为5位
    return s.zfill(5)


def _normalize_us_stock(s: str) -> str:
    """美股: 去掉交易所前缀，大写，保留合法 ticker 格式。"""
    s = s.upper()
    # 去掉交易所前缀 (nasdaq:, nyse:, amex:)
    s = re.sub(r'^(NASDAQ|NYSE|AMEX):', '', s)
    # 美股 ticker: 1-5 个字母，可选 . 或 - 加上 1-3 个字母后缀
    if not re.match(r'^[A-Z]{1,5}([.\-][A-Z]{1,3})?$', s):
        raise ValueError(f"美股代码格式不合法: {s!r}")
    return s


# ============================================================
# 标准化标的键
# ============================================================

_MARKET_TO_CODE = {
    "A股": "CN",
    "美股": "US",
    "港股": "HK",
    "指数": "INDEX",
}


def instrument_key(symbol: str, market: str) -> str:
    """生成标准化标的键。

    示例:
        CN:600519
        US:AAPL
        HK:00700
        INDEX:000300

    Raises:
        ValueError: market 或 symbol 不合法。
    """
    market = normalize_market(market)
    symbol = normalize_symbol(symbol, market)
    code = _MARKET_TO_CODE.get(market)
    if code is None:
        raise ValueError(f"未知市场: {market!r}")
    return f"{code}:{symbol}"
