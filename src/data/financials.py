"""
Financial Statement Fetcher — 三张报表 + 历史基本面序列

资产负债表 / 利润表 / 现金流量表 via akshare
历史 PE/PB/ROE/ROA 序列持久化到 SQLite

使用方式:
    from src.data.financials import FinancialDB, fetch_financial_statements
    db = FinancialDB()
    df = db.get_pe_history("600519")
"""

import os
import sqlite3
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta


# ═══════════════════════════════════════════
# 财务报表获取
# ═══════════════════════════════════════════

def fetch_balance_sheet(symbol: str) -> Optional[pd.DataFrame]:
    """资产负债表 — akshare.stock_balance_sheet_by_report_em"""
    try:
        import akshare as ak
        df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        return df
    except Exception as e:
        print(f"[Financials] 资产负债表获取失败 ({symbol}): {e}")
        return None


def fetch_income_statement(symbol: str) -> Optional[pd.DataFrame]:
    """利润表 — akshare.stock_profit_sheet_by_report_em"""
    try:
        import akshare as ak
        df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        return df
    except Exception as e:
        print(f"[Financials] 利润表获取失败 ({symbol}): {e}")
        return None


def fetch_cash_flow(symbol: str) -> Optional[pd.DataFrame]:
    """现金流量表 — akshare.stock_cash_flow_sheet_by_report_em"""
    try:
        import akshare as ak
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        return df
    except Exception as e:
        print(f"[Financials] 现金流量表获取失败 ({symbol}): {e}")
        return None


def fetch_all_statements(symbol: str) -> Dict[str, Optional[pd.DataFrame]]:
    """一次性获取三张报表"""
    return {
        "balance_sheet": fetch_balance_sheet(symbol),
        "income_statement": fetch_income_statement(symbol),
        "cash_flow": fetch_cash_flow(symbol),
    }


# ═══════════════════════════════════════════
# 历史基本面序列
# ═══════════════════════════════════════════

def fetch_pe_history(symbol: str) -> Optional[pd.DataFrame]:
    """PE 历史序列 — akshare.stock_a_lg_indicator"""
    try:
        import akshare as ak
        df = ak.stock_a_lg_indicator(symbol=symbol)
        if df is None or df.empty:
            return None
        pe_col = [c for c in df.columns if "pe" in c.lower() or "市盈率" in c]
        if not pe_col:
            return None
        result = df[["trade_date", pe_col[0]]].copy()
        result.columns = ["date", "pe"]
        result["date"] = pd.to_datetime(result["date"])
        result["pe"] = pd.to_numeric(result["pe"], errors="coerce")
        return result.dropna()
    except Exception as e:
        print(f"[Financials] PE历史获取失败 ({symbol}): {e}")
        return None


def fetch_pb_history(symbol: str) -> Optional[pd.DataFrame]:
    """PB 历史序列"""
    try:
        import akshare as ak
        df = ak.stock_a_lg_indicator(symbol=symbol)
        if df is None or df.empty:
            return None
        pb_col = [c for c in df.columns if "pb" in c.lower() or "市净率" in c]
        if not pb_col:
            return None
        result = df[["trade_date", pb_col[0]]].copy()
        result.columns = ["date", "pb"]
        result["date"] = pd.to_datetime(result["date"])
        result["pb"] = pd.to_numeric(result["pb"], errors="coerce")
        return result.dropna()
    except Exception:
        return None


def fetch_roe_history(symbol: str) -> Optional[pd.DataFrame]:
    """ROE 历史 — 从财务分析指标获取"""
    try:
        import akshare as ak
        df = ak.stock_financial_analysis_indicator(symbol=symbol)
        if df is None or df.empty:
            return None
        roe_col = [c for c in df.columns if "净资产收益率" in c and "加权" in c]
        if not roe_col:
            roe_col = [c for c in df.columns if "净资产收益率" in c]
        if not roe_col:
            return None
        date_col = [c for c in df.columns if "日期" in c or "报告期" in c or "截止" in c]
        date_col = date_col[0] if date_col else df.columns[0]
        result = df[[date_col, roe_col[0]]].copy()
        result.columns = ["date", "roe"]
        result["date"] = pd.to_datetime(result["date"])
        result["roe"] = pd.to_numeric(result["roe"], errors="coerce")
        return result.dropna()
    except Exception:
        return None


# ═══════════════════════════════════════════
# FinancialDB — 持久化存储
# ═══════════════════════════════════════════

class FinancialDB:
    """基本面数据库 — SQLite 持久化 PE/PB/ROE 历史序列"""

    DB_PATH = os.path.join(
        os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", "D:/trading_data")),
        "financial_series.db"
    )

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            for table in ["pe_history", "pb_history", "roe_history"]:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        symbol TEXT NOT NULL,
                        date TEXT NOT NULL,
                        value REAL NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (symbol, date)
                    )
                """)
                conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_symbol_date
                    ON {table}(symbol, date)
                """)
            conn.commit()

    def store_series(self, symbol: str, indicator: str, df: pd.DataFrame):
        """存储一条历史序列"""
        table_map = {"pe": "pe_history", "pb": "pb_history", "roe": "roe_history"}
        table = table_map.get(indicator)
        if not table:
            raise ValueError(f"不支持的指标: {indicator}")

        if df is None or df.empty:
            return

        now = datetime.now().isoformat()
        value_col = [c for c in df.columns if c != "date"][0]

        with self._conn() as conn:
            for _, row in df.iterrows():
                date_str = str(row["date"])[:10]
                val = float(row[value_col])
                conn.execute(f"""
                    INSERT OR REPLACE INTO {table} (symbol, date, value, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (symbol, date_str, val, now))
            conn.commit()

    def get_series(self, symbol: str, indicator: str,
                   start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取一条历史序列"""
        table_map = {"pe": "pe_history", "pb": "pb_history", "roe": "roe_history"}
        table = table_map.get(indicator)
        if not table:
            raise ValueError(f"不支持的指标: {indicator}")

        query = f"SELECT date, value FROM {table} WHERE symbol = ?"
        params = [symbol]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        with self._conn() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()

        if not rows:
            return pd.DataFrame(columns=["date", indicator])

        df = pd.DataFrame(rows, columns=["date", indicator])
        df["date"] = pd.to_datetime(df["date"])
        return df

    def needs_update(self, symbol: str) -> bool:
        """检查是否需要更新 (数据是否超过 7 天)"""
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT MAX(updated_at) FROM ("
                "  SELECT MAX(updated_at) as updated_at FROM pe_history WHERE symbol = ?"
                "  UNION ALL"
                "  SELECT MAX(updated_at) FROM pb_history WHERE symbol = ?"
                "  UNION ALL"
                "  SELECT MAX(updated_at) FROM roe_history WHERE symbol = ?"
                ")",
                (symbol, symbol, symbol)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return True
            try:
                last = datetime.fromisoformat(row[0])
                return (datetime.now() - last).days > 7
            except ValueError:
                return True

    def get_pe_series(self, symbol: str) -> pd.DataFrame:
        return self.get_series(symbol, "pe")

    def get_pb_series(self, symbol: str) -> pd.DataFrame:
        return self.get_series(symbol, "pb")

    def get_roe_series(self, symbol: str) -> pd.DataFrame:
        return self.get_series(symbol, "roe")


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

financial_db = FinancialDB()
