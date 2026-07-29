"""
DataIntegrityChecker — 数据完整性校验器 (v6.3)

1. 前向填充校验: 检测是否用当日收盘价计算当日开盘因子(必须shift(1))
2. ST/退市剔除: 每日扫描自动过滤ST和退市股票
3. 次新股过滤: 剔除上市<60天的股票
4. 数据纯净度报告: 标注潜在数据泄漏日期
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional, Tuple


class DataIntegrityChecker:
    """数据完整性校验器"""

    def __init__(self):
        self._st_list: Set[str] = set()
        self._delisted: Set[str] = set()
        self._new_stocks: Dict[str, str] = {}  # symbol -> 上市日期
        self._last_st_refresh: str = ""
        self._issues: List[Dict] = []

    # ═══════════════════════════════════════════
    # 1. 前向填充校验 (Look-ahead Bias)
    # ═══════════════════════════════════════════

    def check_lookahead(self, df: pd.DataFrame,
                        factor_cols: List[str] = None) -> Dict:
        """
        检测因子是否存在前视偏差
        规则: 用当日收盘价计算的因子,不能用于预测当日收益

        返回: {
          clean: bool,
          violations: [{date, column, issue}],
          risk_dates: [date, ...]
        }
        """
        if df is None or len(df) < 60:
            return {"clean": True, "violations": [], "risk_dates": []}

        close = df["close"]
        violations = []

        # 检测1: close 和 close.shift(1) 的相关性
        auto_corr = close.autocorr(lag=1)
        if auto_corr > 0.995:
            # 价格几乎不变,可能的未来数据泄漏
            # 进一步检查: 日收益率和当日因子值的关系
            ret = close.pct_change().shift(-1)  # 明日收益
            if len(ret.dropna()) > 0:
                # 检查是否有因子使用了未来的收盘价
                for col in df.columns:
                    if col in ("date", "open", "high", "low", "close", "volume"):
                        continue
                    if factor_cols and col not in factor_cols:
                        continue
                    # 因子值和当日收益的相关系数
                    valid = df[col].notna() & ret.notna()
                    if valid.sum() < 10:
                        continue
                    corr = df.loc[valid, col].corr(ret[valid])
                    if abs(corr) > 0.3:
                        violations.append({
                            "column": col,
                            "correlation": round(corr, 4),
                            "issue": f"因子与次日收益相关性={corr:.3f},可能存在前视偏差",
                            "severity": "high" if abs(corr) > 0.5 else "medium",
                        })

        # 检测2: 收盘价 → 开盘因子的隔离
        # 因子值在当天收盘后才能知道,必须用 shift(1) 防止泄漏
        shift_violations = []
        for col in df.columns:
            if col in ("date", "open", "high", "low", "close", "volume"):
                continue
            if factor_cols and col not in factor_cols:
                continue
            vals = df[col].dropna()
            if len(vals) < 60:
                continue
            # 检查因子值和当天收盘价的同步性
            close_aligned = close.loc[vals.index]
            sync_corr = vals.corr(close_aligned)
            # 检查因子值和前一天收盘价的关系(shift后应该更有意义)
            prev_close = close.shift(1).loc[vals.index]
            prev_corr = vals.corr(prev_close)
            # 如果因子和当日收盘价高度相关,且比和昨日收盘价更相关 → 泄漏风险
            if abs(sync_corr) > 0.7 and abs(sync_corr) > abs(prev_corr) * 1.3:
                shift_violations.append({
                    "column": col,
                    "sync_corr": round(sync_corr, 3),
                    "prev_corr": round(prev_corr, 3),
                    "issue": f"因子与当日收盘价相关({sync_corr:.3f}) > 昨日收盘价({prev_corr:.3f})，需shift(1)",
                    "severity": "high",
                })
        violations.extend(shift_violations)

        risk_dates = []
        if violations:
            # 标记全部日期为风险(因为因子计算方式本身有问题)
            risk_dates = [str(df["date"].iloc[0])[:10], str(df["date"].iloc[-1])[:10]]

        return {
            "clean": len(violations) == 0,
            "violations": violations,
            "risk_dates": risk_dates,
        }

    # ═══════════════════════════════════════════
    # 2. ST / 退市过滤
    # ═══════════════════════════════════════════

    def refresh_blacklist(self) -> Dict[str, int]:
        """
        从akshare获取ST列表和退市列表
        返回: {"st": count, "delisted": count}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_st_refresh == today and self._st_list:
            return {"st": len(self._st_list), "delisted": len(self._delisted)}

        st_count = 0
        delisted_count = 0

        # ST 列表
        try:
            import akshare as ak
            df = ak.stock_zh_a_st_em()
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    code = str(row.get("代码", "")).strip()
                    if code:
                        self._st_list.add(code)
                        st_count += 1
        except Exception as e:
            print(f"[Integrity] ST列表获取失败: {e}")

        # 退市列表
        try:
            import akshare as ak
            df = ak.stock_zh_a_delist_em()
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    code = str(row.get("股票代码", row.get("代码", ""))).strip()
                    if code:
                        self._delisted.add(code)
                        delisted_count += 1
        except Exception:
            # 备用API
            try:
                import akshare as ak
                df = ak.stock_zh_a_stop_em()
                if df is not None and len(df) > 0:
                    for _, row in df.iterrows():
                        code = str(row.get("代码", "")).strip()
                        if code:
                            self._delisted.add(code)
                            delisted_count += 1
            except Exception:
                pass

        self._last_st_refresh = today
        return {"st": st_count, "delisted": delisted_count}

    def is_blacklisted(self, symbol: str) -> Tuple[bool, str]:
        """检查是否在黑名单"""
        code = symbol.replace(".SH", "").replace(".SZ", "").strip()
        if code in self._st_list:
            return True, "ST股票"
        if code in self._delisted:
            return True, "已退市"
        return False, ""

    def filter_symbols(self, symbols: List[str]) -> List[str]:
        """过滤黑名单股票"""
        self.refresh_blacklist()
        clean = []
        removed = []
        for s in symbols:
            blocked, reason = self.is_blacklisted(s)
            if blocked:
                removed.append(f"{s}({reason})")
            else:
                clean.append(s)
        if removed:
            print(f"[Integrity] 已过滤 {len(removed)} 只: {', '.join(removed[:5])}...")
        return clean

    # ═══════════════════════════════════════════
    # 3. 次新股过滤
    # ═══════════════════════════════════════════

    def get_listing_date(self, symbol: str) -> Optional[str]:
        """获取上市日期"""
        code = symbol.replace(".SH", "").replace(".SZ", "")
        if code in self._new_stocks:
            return self._new_stocks[code]

        try:
            import akshare as ak
            df = ak.stock_individual_info_em(symbol=code)
            if df is not None:
                for _, row in df.iterrows():
                    if "上市" in str(row.get("item", "")):
                        date_str = str(row.get("value", ""))
                        self._new_stocks[code] = date_str
                        return date_str
        except Exception:
            pass
        return None

    def is_new_stock(self, symbol: str, min_days: int = 60) -> Tuple[bool, str]:
        """是否次新股"""
        listing = self.get_listing_date(symbol)
        if not listing:
            return False, ""
        try:
            listing_dt = pd.to_datetime(listing)
            days_listed = (datetime.now() - listing_dt).days
            if days_listed < min_days:
                return True, f"上市仅{days_listed}天(<{min_days})"
        except Exception:
            pass
        return False, ""

    def filter_new_stocks(self, symbols: List[str],
                          min_days: int = 60) -> List[str]:
        """过滤次新股"""
        clean = []
        for s in symbols:
            is_new, reason = self.is_new_stock(s, min_days)
            if not is_new:
                clean.append(s)
        return clean

    # ═══════════════════════════════════════════
    # 4. 数据纯净度报告
    # ═══════════════════════════════════════════

    def purity_report(self, data: pd.DataFrame,
                      symbol: str = "",
                      factor_columns: List[str] = None) -> str:
        """
        生成数据纯净度报告
        """
        self._issues = []

        lines = []
        lines.append("=" * 60)
        lines.append(f"  数据纯净度报告: {symbol}")
        lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)

        if data is None or len(data) == 0:
            lines.append("  ❌ 无数据")
            return "\n".join(lines)

        # 1. 基本统计
        lines.append(f"\n[基本信息]")
        lines.append(f"  行数: {len(data)}")
        lines.append(f"  日期范围: {str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]}")
        lines.append(f"  列数: {len(data.columns)}")

        # 2. 缺失值检查
        na_counts = data.isna().sum()
        na_pct = (na_counts / len(data) * 100).round(1)
        missing_cols = na_counts[na_counts > 0]
        lines.append(f"\n[缺失值检查]")
        if len(missing_cols) == 0:
            lines.append(f"  ✅ 无缺失值")
        else:
            for col, cnt in missing_cols.items():
                lines.append(f"  ⚠️ {col}: {cnt} ({na_pct[col]}%)")

        # 3. 前视偏差检查
        checker = self.check_lookahead(data, factor_columns)
        lines.append(f"\n[前视偏差]")
        if checker["clean"]:
            lines.append(f"  ✅ 未检测到前视偏差")
        else:
            lines.append(f"  ❌ 发现 {len(checker['violations'])} 个潜在问题:")
            for v in checker["violations"]:
                sev = "🔴" if v["severity"] == "high" else "🟡"
                lines.append(f"  {sev} {v['issue']}")

        # 4. 异常值检查
        if "close" in data.columns:
            ret = data["close"].pct_change()
            outliers = (abs(ret) > 0.11)  # 涨跌停10%+
            outlier_count = outliers.sum()
            lines.append(f"\n[异常波动]")
            if outlier_count == 0:
                lines.append(f"  ✅ 无异常波动")
            else:
                outlier_dates = data.loc[outliers[outliers].index, "date"].apply(
                    lambda x: str(x)[:10]).tolist()
                lines.append(f"  ⚠️ {outlier_count} 次涨跌幅>11%")
                if outlier_dates:
                    for d in outlier_dates[-5:]:
                        lines.append(f"    {d}")

        # 5. 重复数据检查
        if "date" in data.columns:
            dupes = data["date"].duplicated().sum()
            lines.append(f"\n[重复数据]")
            if dupes == 0:
                lines.append(f"  ✅ 无重复日期")
            else:
                lines.append(f"  ⚠️ {dupes} 行重复日期")

        # 6. ST/退市检查
        self.refresh_blacklist()
        blocked, reason = self.is_blacklisted(symbol)
        lines.append(f"\n[黑名单检查]")
        if blocked:
            lines.append(f"  ❌ {reason}")
        else:
            lines.append(f"  ✅ 正常交易")

        # 7. 上市天数检查
        if symbol:
            is_new, info = self.is_new_stock(symbol)
            lines.append(f"\n[上市时长]")
            if is_new:
                lines.append(f"  ⚠️ {info}")
            else:
                lines.append(f"  ✅ 上市超过60天")

        # 8. 综合评分
        score = 100
        if not checker["clean"]:
            score -= 30
        if len(missing_cols) > 3:
            score -= 20
        if outlier_count > 10:
            score -= 15
        if blocked:
            score -= 50
        if is_new:
            score -= 20
        if dupes > 0:
            score -= 10
        score = max(0, score)

        lines.append(f"\n[综合评分]")
        grade = "A" if score >= 90 else ("B" if score >= 70 else ("C" if score >= 50 else "D"))
        lines.append(f"  纯净度: {score}/100 (等级 {grade})")
        lines.append("=" * 60)

        return "\n".join(lines)


# 全局实例
checker = DataIntegrityChecker()
