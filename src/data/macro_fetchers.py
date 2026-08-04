"""
Macro Data Fetchers — 真实宏观数据连接 (akshare)

为 src/backtest/macro.py 中预定义的 8 个指标注册真实 akshare 数据抓取器。

使用方式:
    from src.data.macro_fetchers import register_all_macro_fetchers
    registry = register_all_macro_fetchers()
    df = registry.get("CN_CPI_YOY").fetch("CN_CPI_YOY", "2020-01-01", "2024-12-31")
"""

import pandas as pd
from typing import Optional
from datetime import datetime


def _clean_date(df: pd.DataFrame, date_col: str, value_col: str,
                start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """将 akshare 返回的 DataFrame 标准化为 {date, value} 格式"""
    df = df.rename(columns={date_col: "date", value_col: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df.sort_values("date")

    if start_date:
        df = df[df["date"] >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df["date"] <= pd.Timestamp(end_date)]

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df[["date", "value"]].reset_index(drop=True)


# ═══════════════════════════════════════════
# China Macro Fetchers
# ═══════════════════════════════════════════

def fetch_cn_cpi_yoy(code: str = None, start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
    """中国 CPI 当月同比 — akshare.macro_china_cpi_monthly"""
    try:
        import akshare as ak
        df = ak.macro_china_cpi_monthly()
        # columns: 日期, 全国-当月, 全国-累计, 城市-当月, ...
        result = df[["日期", "全国-当月"]].copy()
        result["全国-当月"] = pd.to_numeric(result["全国-当月"], errors="coerce")
        return _clean_date(result, "日期", "全国-当月", start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] CN_CPI_YOY fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_cn_ppi_yoy(code: str = None, start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
    """中国 PPI 当月同比 — akshare.macro_china_ppi"""
    try:
        import akshare as ak
        df = ak.macro_china_ppi()
        result = df[["日期", "当月"]].copy()
        return _clean_date(result, "日期", "当月", start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] CN_PPI_YOY fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_cn_pmi(code: str = None, start_date: str = None,
                 end_date: str = None) -> pd.DataFrame:
    """中国制造业 PMI — akshare.macro_china_pmi"""
    try:
        import akshare as ak
        df = ak.macro_china_pmi()
        # 取制造业PMI列
        pmi_col = [c for c in df.columns if "制造业" in c or "PMI" in c]
        if not pmi_col:
            pmi_col = df.columns[1]  # fallback
        else:
            pmi_col = pmi_col[0]
        result = df[["日期", pmi_col]].copy()
        return _clean_date(result, "日期", pmi_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] CN_PMI fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_cn_lpr_1y(code: str = None, start_date: str = None,
                    end_date: str = None) -> pd.DataFrame:
    """中国 LPR 1年期 — akshare.macro_china_lpr"""
    try:
        import akshare as ak
        df = ak.macro_china_lpr()
        # 取1年期LPR列
        lpr_cols = [c for c in df.columns if "1年" in c or "一年" in c]
        if not lpr_cols:
            lpr_cols = [c for c in df.columns if "LPR" in c]
        lpr_col = lpr_cols[0] if lpr_cols else df.columns[-1]
        result = df[["日期", lpr_col]].copy()
        return _clean_date(result, "日期", lpr_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] CN_LPR_1Y fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


# ═══════════════════════════════════════════
# US Macro Fetchers
# ═══════════════════════════════════════════

def fetch_us_cpi_yoy(code: str = None, start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
    """美国 CPI 当月同比 — akshare.macro_usa_cpi_monthly"""
    try:
        import akshare as ak
        df = ak.macro_usa_cpi_monthly()
        val_col = [c for c in df.columns if "同比" in c or "CPI" in c]
        val_col = val_col[0] if val_col else df.columns[1]
        result = df[["日期", val_col]].copy()
        return _clean_date(result, "日期", val_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] US_CPI_YOY fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_us_fed_funds(code: str = None, start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
    """美国联邦基金利率 — akshare.macro_usa_interest_rate"""
    try:
        import akshare as ak
        df = ak.macro_usa_interest_rate()
        # 取联邦基金利率
        rate_cols = [c for c in df.columns if "联邦基金" in c or "利率" in c]
        rate_col = rate_cols[0] if rate_cols else df.columns[1]
        result = df[["日期", rate_col]].copy()
        return _clean_date(result, "日期", rate_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] US_FED_FUNDS fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_us_unemployment(code: str = None, start_date: str = None,
                          end_date: str = None) -> pd.DataFrame:
    """美国失业率 — akshare.macro_usa_unemployment_rate"""
    try:
        import akshare as ak
        df = ak.macro_usa_unemployment_rate()
        val_col = [c for c in df.columns if "失业" in c or "率" in c]
        val_col = val_col[0] if val_col else df.columns[1]
        result = df[["日期", val_col]].copy()
        return _clean_date(result, "日期", val_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] US_UNEMPLOYMENT fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


def fetch_us_10y_yield(code: str = None, start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
    """美国 10 年期国债收益率 — akshare.bond_zh_us_rate"""
    try:
        import akshare as ak
        df = ak.bond_zh_us_rate()
        col_10y = [c for c in df.columns if "10" in c and ("年" in c or "Y" in c.upper())]
        rate_col = col_10y[0] if col_10y else df.columns[1]
        result = df[["日期", rate_col]].copy()
        return _clean_date(result, "日期", rate_col, start_date, end_date)
    except Exception as e:
        print(f"[MacroFetcher] US_10Y_YIELD fetch failed: {e}")
        return pd.DataFrame(columns=["date", "value"])


# ═══════════════════════════════════════════
# 注册到 MacroProviderRegistry
# ═══════════════════════════════════════════

FETCHER_MAP = {
    "CN_CPI_YOY": fetch_cn_cpi_yoy,
    "CN_PPI_YOY": fetch_cn_ppi_yoy,
    "CN_PMI": fetch_cn_pmi,
    "CN_LPR_1Y": fetch_cn_lpr_1y,
    "US_CPI_YOY": fetch_us_cpi_yoy,
    "US_FED_FUNDS": fetch_us_fed_funds,
    "US_UNEMPLOYMENT": fetch_us_unemployment,
    "US_10Y_YIELD": fetch_us_10y_yield,
}


def register_all_macro_fetchers():
    """将所有 akshare 宏观数据抓取器注册到 MacroProviderRegistry"""
    from src.backtest.macro import (
        MacroProviderRegistry, CallableMacroProvider, macro_registry
    )
    for code, fetcher in FETCHER_MAP.items():
        try:
            provider = CallableMacroProvider(code, fetcher)
            if code in [p.name for p in macro_registry.providers]:
                macro_registry.register(provider, replace=True)
            else:
                macro_registry.register(provider)
        except Exception as e:
            print(f"[MacroFetcher] 注册 {code} 失败: {e}")

    return macro_registry


# ═══════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════

def get_macro_data(code: str, start_date: str = None,
                   end_date: str = None) -> pd.DataFrame:
    """一键获取宏观数据"""
    code = code.strip().upper()
    if code in FETCHER_MAP:
        return FETCHER_MAP[code](code, start_date=start_date, end_date=end_date)
    raise ValueError(f"不支持的宏观代码: {code}, 可用: {list(FETCHER_MAP.keys())}")
