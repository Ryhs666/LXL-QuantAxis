"""
实时行情采集器 — 腾讯财经API

多股票批量查询 → 统一内部格式 → 推送到回调/SocketIO
支持自动重连、数据校验、降级到模拟器。
"""

import time
import threading
import logging
from datetime import datetime
from typing import Callable, Optional

import requests

from src.config import config

logger = logging.getLogger("realtime.collector")

# 内部统一格式模板
EMPTY_TICK = {
    "symbol": "", "name": "", "price": 0.0, "open": 0.0,
    "high": 0.0, "low": 0.0, "volume": 0, "change": 0.0,
    "change_pct": 0.0, "pre_close": 0.0, "timestamp": "",
}


def fetch_tencent_batch(symbols: list) -> dict:
    """
    腾讯财经批量行情接口。

    参数:
        symbols: 股票代码列表，如 ["000001", "600519"]

    返回:
        {"000001": {"price": 12.34, ...}, "600519": {...}}
        请求失败返回空字典
    """
    if not symbols:
        return {}

    # 构建查询参数：sh600519,sz000001
    codes = []
    for s in symbols:
        prefix = "sh" if s.startswith(("6", "9")) else "sz"
        codes.append(f"{prefix}{s}")

    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    try:
        resp = requests.get(url, timeout=5,
                           headers={"User-Agent": "Mozilla/5.0"})
        resp.encoding = "gbk"
        text = resp.text
    except Exception as e:
        logger.warning(f"腾讯行情请求失败: {e}")
        return {}

    results = {}
    # 解析每一行：v_sh600519="1~贵州茅台~600519~..."
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or '="' not in line or "~" not in line:
            continue
        try:
            # 提取 symbol
            var_name = line.split("=")[0]  # v_sh600519
            raw_code = var_name.replace("v_", "").replace("sh", "").replace("sz", "")
            # 提取数据部分
            data_str = line.split('="')[1].rstrip('";')
            parts = data_str.split("~")

            if len(parts) < 40:
                continue

            price = _safe_float(parts[3])
            if price <= 0:
                continue

            pre_close = _safe_float(parts[4])
            tick = {
                "symbol": raw_code,
                "name": parts[1] if len(parts) > 1 else raw_code,
                "price": price,
                "open": _safe_float(parts[5]),
                "high": _safe_float(parts[33]) if len(parts) > 33 else price,
                "low": _safe_float(parts[34]) if len(parts) > 34 else price,
                "volume": _safe_int(parts[6]),
                "change": round(price - pre_close, 2),
                "change_pct": round((price / pre_close - 1) * 100, 2) if pre_close > 0 else 0.0,
                "pre_close": pre_close,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
            results[raw_code] = tick
        except Exception as e:
            logger.debug(f"解析行失败: {line[:50]}... {e}")

    return results


def _safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default


class RealtimeCollector:
    """
    实时行情采集器（后台线程）。

    用法:
        collector = RealtimeCollector(callback=on_tick)
        collector.start()   # 后台线程开始轮询
        collector.stop()    # 停止
    """

    def __init__(
        self,
        symbols: list = None,
        callback: Callable = None,
        poll_interval: int = None,
    ):
        self.symbols = symbols or config.get("realtime_symbols", [])
        self.callback = callback          # 每收到一批数据回调: fn({symbol: tick})
        self.poll_interval = poll_interval or config.get("realtime_poll_interval", 3)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_data: dict = {}        # 上次成功数据，用于降级
        self._fail_count = 0
        self._success_count = 0

    def start(self):
        """启动后台采集线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"采集器启动: {len(self.symbols)} 只股票, {self.poll_interval}s间隔")

    def stop(self):
        """停止采集"""
        self._running = False
        logger.info("采集器已停止")

    def _run_loop(self):
        """后台循环：轮询 → 回调 → 等待"""
        while self._running:
            try:
                data = fetch_tencent_batch(self.symbols)
                if data:
                    self._last_data = data
                    self._fail_count = 0
                    self._success_count += 1
                    if self.callback:
                        self.callback(data)
                else:
                    self._fail_count += 1
                    logger.warning(f"采集失败 (#{self._fail_count})，下次重试")
                    if self._fail_count > 5:
                        # 超过5次失败，降级：用上次数据保持价格微调
                        self._emit_degraded()

                # 等待下次轮询
                time.sleep(self.poll_interval)

            except Exception as e:
                self._fail_count += 1
                logger.error(f"采集异常: {e}")
                time.sleep(config.get("realtime_retry_interval", 10))

    def _emit_degraded(self):
        """降级模式：基于上次数据微调价格，保持前端不卡死"""
        if not self._last_data or not self.callback:
            return
        import random
        degraded = {}
        for sym, tick in self._last_data.items():
            d = dict(tick)
            wiggle = 1 + random.uniform(-0.001, 0.001)
            d["price"] = round(d["price"] * wiggle, 2)
            d["change"] = round(d["price"] - d["open"], 2)
            d["change_pct"] = round((d["price"] / d["open"] - 1) * 100, 2) if d["open"] > 0 else 0
            d["timestamp"] = datetime.now().strftime("%H:%M:%S")
            degraded[sym] = d
        self.callback(degraded)

    @property
    def stats(self):
        return {
            "symbols": len(self.symbols),
            "running": self._running,
            "success": self._success_count,
            "fail": self._fail_count,
            "last_update": datetime.now().strftime("%H:%M:%S"),
        }
