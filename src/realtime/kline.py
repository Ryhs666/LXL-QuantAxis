"""
实时K线聚合模块

将 Tick 级行情聚合为 1分钟/5分钟/15分钟 K 线，
维护内存缓存，闭合时通过 SocketIO 推送。

用法:
    from src.realtime.kline import KLineAggregator, KLINE_CACHE
    agg = KLineAggregator(socketio=socketio)
    agg.on_tick("000001", 12.34, 50000)
"""

import time
import threading
from datetime import datetime
from typing import Optional
import pandas as pd
import os

# 全局K线缓存
KLINE_CACHE: dict = {}  # {symbol: {"1min": [...], "5min": [...], "15min": [...]}}

# 每种周期的秒数
PERIOD_SECONDS = {"1min": 60, "5min": 300, "15min": 900, "30min": 1800, "60min": 3600}


def _period_key(ts: datetime, period: str) -> str:
    """返回该时间戳所属K线周期的标识key"""
    secs = PERIOD_SECONDS.get(period, 60)
    minute_of_day = ts.hour * 60 + ts.minute
    bucket = (minute_of_day // (secs // 60)) * (secs // 60)
    h = bucket // 60
    m = bucket % 60
    return f"{h:02d}:{m:02d}"


def _now():
    return datetime.now()


class KLineAggregator:
    """K线聚合器 — 嵌在行情回调中使用"""

    def __init__(self, socketio=None, max_bars: int = 1000, signal_callback=None):
        self.socketio = socketio
        self.max_bars = max_bars
        self.signal_callback = signal_callback  # K线闭合时调用: fn(symbol, period, bar)
        self._current: dict = {}
        self._lock = threading.Lock()
        # 初始化缓存
        for sym in []:
            if sym not in KLINE_CACHE:
                KLINE_CACHE[sym] = {p: [] for p in PERIOD_SECONDS}

    def on_tick(self, symbol: str, price: float, volume: int = 0):
        """行情回调：聚合到三个周期"""
        if price <= 0:
            return
        now = _now()
        # 首次调用打印
        if not hasattr(self, '_debug_printed'):
            self._debug_printed = True
            print(f"[KLine] 聚合器开始接收tick: {symbol} ¥{price}")

        # 只聚合交易时段（9:30-15:00 简化，实际取9:00-16:00范围）
        # 非交易时段也聚合，方便测试

        for period in ("1min", "5min", "15min"):
            self._aggregate(symbol, period, now, price, volume)

    def _aggregate(self, symbol: str, period: str, ts: datetime,
                   price: float, volume: int):
        """对单个周期进行聚合"""
        key = _period_key(ts, period)

        with self._lock:
            # 初始化缓存
            if symbol not in KLINE_CACHE:
                KLINE_CACHE[symbol] = {p: [] for p in PERIOD_SECONDS}

            # 初始化当前K线跟踪
            if symbol not in self._current:
                self._current[symbol] = {}
            if period not in self._current[symbol]:
                self._current[symbol][period] = None

            cur = self._current[symbol][period]
            bars = KLINE_CACHE[symbol][period]

            # 新周期 → 闭合旧K线，新建K线
            if cur is None or cur["key"] != key:
                # 闭合上一根
                if cur is not None:
                    bar = {
                        "time": cur["time"],
                        "open": cur["open"],
                        "high": cur["high"],
                        "low": cur["low"],
                        "close": cur["close"],
                        "volume": cur["volume"],
                    }
                    bars.append(bar)
                    # 限制数量
                    if len(bars) > self.max_bars:
                        bars.pop(0)

                    # 推送到前端
                    self._emit_kline(symbol, period, bars)
                    # K线闭合 → 触发策略信号计算
                    if self.signal_callback:
                        try:
                            self.signal_callback(symbol, period, bar)
                        except Exception:
                            pass

                # 新建
                self._current[symbol][period] = {
                    "key": key,
                    "time": ts.strftime("%H:%M"),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                }
            else:
                # 同周期内更新
                cur["high"] = max(cur["high"], price)
                cur["low"] = min(cur["low"], price)
                cur["close"] = price
                cur["volume"] += volume

    def _emit_kline(self, symbol: str, period: str, bars: list):
        """推送K线数据到前端"""
        if not self.socketio:
            print(f"[KLine] WARN: socketio未设置，无法推送 {symbol} {period}")
            return
        print(f"[KLine] 推送 {symbol} {period} {len(bars)}根K线 最新¥{bars[-1]['close']}")

        # 取最近60根（减少传输量）
        recent = bars[-60:] if len(bars) > 60 else bars

        # 计算涨跌幅
        change_pct = 0.0
        if len(bars) >= 2:
            first_close = bars[0]["close"] if bars[0]["close"] > 0 else bars[0]["open"]
            latest = bars[-1]["close"]
            if first_close > 0:
                change_pct = round((latest / first_close - 1) * 100, 2)

        latest_price = bars[-1]["close"] if bars else 0

        try:
            self.socketio.emit('kline_update', {
                "symbol": symbol,
                "period": period,
                "data": recent,
                "latest_price": latest_price,
                "change_pct": change_pct,
            })
        except Exception:
            pass

    def get_bars(self, symbol: str, period: str = "5min") -> list:
        """获取某只股票的K线数据（含未闭合）"""
        with self._lock:
            bars = list(KLINE_CACHE.get(symbol, {}).get(period, []))
            cur = self._current.get(symbol, {}).get(period)
            if cur:
                bars.append({
                    "time": cur["time"],
                    "open": cur["open"],
                    "high": cur["high"],
                    "low": cur["low"],
                    "close": cur["close"],
                    "volume": cur["volume"],
                })
            return bars

    def load_history(self, symbol: str):
        """从本地CSV回填最近5天数据到各周期，让图表首次加载不空白"""
        cache_file = f"D:/trading_data/cache/A股_{symbol}_daily.csv"
        if not os.path.exists(cache_file):
            return

        try:
            df = pd.read_csv(cache_file)
            if len(df) < 2:
                return

            recent = df.tail(5)
            with self._lock:
                if symbol not in KLINE_CACHE:
                    KLINE_CACHE[symbol] = {p: [] for p in PERIOD_SECONDS}

                for _, row in recent.iterrows():
                    date_str = str(row.get("date", ""))[:10]
                    o = float(row["open"])
                    h = float(row["high"])
                    l = float(row["low"])
                    c = float(row["close"])
                    v = int(row.get("volume", 0))
                    bar = {"time": date_str, "open": o, "high": h, "low": l, "close": c, "volume": v}

                    # 拆到各周期，15min作日线参考
                    KLINE_CACHE[symbol]["15min"].append(bar)
                    # 每日模拟4个5分钟bar（开/上午/下午/收）
                    KLINE_CACHE[symbol]["5min"].append({"time": date_str+" 10:00", "open": o, "high": max(o,h), "low": min(o,l), "close": (o+h)/2, "volume": v//4})
                    KLINE_CACHE[symbol]["5min"].append({"time": date_str+" 11:00", "open": (o+h)/2, "high": h, "low": min(l,c), "close": (h+l)/2, "volume": v//4})
                    KLINE_CACHE[symbol]["5min"].append({"time": date_str+" 13:00", "open": (h+l)/2, "high": max(h,c), "low": l, "close": (l+c)/2, "volume": v//4})
                    KLINE_CACHE[symbol]["5min"].append({"time": date_str+" 14:30", "open": (l+c)/2, "high": max(h,c), "low": min(l,c), "close": c, "volume": v//4})
                    # 1min: 取2个精简bar
                    KLINE_CACHE[symbol]["1min"].append({"time": date_str+" 09:35", "open": o, "high": h, "low": l, "close": (o+c)/2, "volume": v//2})
                    KLINE_CACHE[symbol]["1min"].append({"time": date_str+" 14:55", "open": (o+c)/2, "high": h, "low": l, "close": c, "volume": v//2})

                # 限制数量
                for p in ("1min", "5min", "15min"):
                    if len(KLINE_CACHE[symbol][p]) > self.max_bars:
                        KLINE_CACHE[symbol][p] = KLINE_CACHE[symbol][p][-self.max_bars:]

                # 推送给前端
                for p in ("1min", "5min", "15min"):
                    self._emit_kline(symbol, p, KLINE_CACHE[symbol][p])

        except Exception:
            pass

    @property
    def stats(self):
        symbols = list(KLINE_CACHE.keys())
        return {
            "symbols": len(symbols),
            "symbol_list": symbols[:10],
        }
