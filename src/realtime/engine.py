"""
实时策略信号引擎

订阅行情数据 → 加载用户策略 → 评估信号 → 存储 + WebSocket推送

架构:
  RealtimeCollector → StrategyEngine.on_tick(data) → evaluate → signal
                                                         ↓
                                              user_trade_logs (DB)
                                              socketio.emit('strategy_signal')
"""

import time
import threading
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional

import pandas as pd
import sqlite3

from src.config import config

logger = logging.getLogger("realtime.engine")

# 信号冷却时间（秒）— 同一用户+策略+股票+方向 在此时间内不重复触发
SIGNAL_COOLDOWN = 300  # 5分钟


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load_ohlcv(symbol: str):
    """从缓存加载股票的OHLCV数据"""
    import os
    from src.lxl_quantaxis.core.config.loader import get_config
    cfg = get_config()
    cache_file = f"{cfg.cache_dir}/A股_{symbol}_daily.csv"
    if not os.path.exists(cache_file):
        return None
    try:
        df = pd.read_csv(cache_file)
        if len(df) < 20:
            return None
        return df
    except Exception:
        return None


def _compute_rsi(close: pd.Series, period: int = 14) -> float:
    """计算最新RSI值"""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean().iloc[-1]
    loss = (-delta).clip(lower=0).rolling(period).mean().iloc[-1]
    if loss == 0:
        return 100.0
    return float(100 - 100 / (1 + gain / loss))


def _compute_ma_cross(close: pd.Series, fast: int = 5, slow: int = 20) -> str:
    """判断均线交叉信号"""
    if len(close) < slow + 2:
        return "HOLD"
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    # 金叉：快线刚从下穿上
    if ma_fast.iloc[-2] <= ma_slow.iloc[-2] and ma_fast.iloc[-1] > ma_slow.iloc[-1]:
        return "BUY"
    # 死叉：快线刚从上穿下
    if ma_fast.iloc[-2] >= ma_slow.iloc[-2] and ma_fast.iloc[-1] < ma_slow.iloc[-1]:
        return "SELL"
    return "HOLD"


class SignalCache:
    """信号冷却缓存 — 防止短时间内重复触发"""

    def __init__(self, cooldown_seconds: int = SIGNAL_COOLDOWN):
        self._cache: dict = {}       # key → timestamp
        self._cooldown = cooldown_seconds
        self._lock = threading.Lock()

    def should_emit(self, user_id: int, strategy: str, symbol: str, action: str) -> bool:
        """检查该信号是否在冷却期内"""
        key = f"{user_id}:{strategy}:{symbol}:{action}"
        now = time.time()
        with self._lock:
            last = self._cache.get(key, 0)
            if now - last < self._cooldown:
                return False
            self._cache[key] = now
            # 清理过期缓存（每100次清理一次）
            if len(self._cache) > 1000:
                self._cache = {k: v for k, v in self._cache.items() if now - v < self._cooldown}
            return True


class StrategyEngine:
    """
    策略信号引擎

    用法:
        engine = StrategyEngine(socketio=socketio)
        # 在行情回调中:
        collector = RealtimeCollector(callback=engine.on_tick)
    """

    def __init__(self, socketio=None):
        self.socketio = socketio
        self.signal_cache = SignalCache()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._stats = {"evaluated": 0, "signals": 0, "errors": 0}

    def on_tick(self, data: dict):
        """行情回调入口 — data: {symbol: tick_dict, ...}"""
        for symbol, tick in data.items():
            self._executor.submit(self._evaluate_symbol, symbol, tick)

    def _evaluate_symbol(self, symbol: str, tick: dict):
        """对单只股票，评估所有关联策略"""
        self._stats["evaluated"] += 1
        price = tick.get("price", 0)
        if price <= 0:
            return

        # 加载历史数据
        df = _load_ohlcv(symbol)
        if df is None:
            return

        # 追加当前tick到末尾（模拟最新bar）
        now_str = datetime.now().strftime("%Y-%m-%d")
        latest = pd.DataFrame([{
            "date": now_str, "open": tick.get("open", price),
            "high": tick.get("high", price), "low": tick.get("low", price),
            "close": price, "volume": tick.get("volume", 0),
        }])
        df = pd.concat([df, latest], ignore_index=True)

        close = df["close"]

        # === 内置信号规则（无需登录，全局策略） ===
        signals = []

        # 1. RSI 超卖超买
        try:
            rsi = _compute_rsi(close)
            if rsi < 25:
                signals.append(("RSI超卖", "BUY", f"RSI={rsi:.0f} 深度超卖，反弹概率大"))
            elif rsi > 80:
                signals.append(("RSI超买", "SELL", f"RSI={rsi:.0f} 严重超买，注意回调"))
        except Exception:
            pass

        # 2. 均线交叉
        try:
            cross = _compute_ma_cross(close, 5, 20)
            if cross == "BUY":
                signals.append(("MA金叉", "BUY", "MA5上穿MA20，短线看涨"))
            elif cross == "SELL":
                signals.append(("MA死叉", "SELL", "MA5下穿MA20，短线看跌"))
        except Exception:
            pass

        # 3. 布林带位置
        try:
            ma20 = close.rolling(20).mean().iloc[-1]
            std20 = close.rolling(20).std().iloc[-1]
            bb_lower = ma20 - 2 * std20
            bb_upper = ma20 + 2 * std20
            if price <= bb_lower:
                signals.append(("布林下轨", "BUY", f"触及布林下轨{bb_lower:.2f}，支撑较强"))
            elif price >= bb_upper:
                signals.append(("布林上轨", "SELL", f"触及布林上轨{bb_upper:.2f}，压力较大"))
        except Exception:
            pass

        # 加载用户策略配置
        user_strategies = self._load_user_strategies(symbol)

        # === 关联用户策略 → 扩展信号 ===
        extended = []
        for sname, action, reason in signals:
            # 全局信号（user_id=0）
            extended.append((0, "全局策略", sname, action, reason))
            # 每个用户策略
            for us in user_strategies:
                extended.append((us["user_id"], us["name"], sname, action, reason))

        # === 处理信号：冷却检查 → 写DB → 推送 ===
        for uid, strategy_name, signal_type, action, reason in extended:
            if not self.signal_cache.should_emit(uid, strategy_name, symbol, action):
                continue

            # 写入数据库
            self._save_signal(uid, symbol, tick.get("name", ""), action, price, reason)

            # WebSocket 推送
            if self.socketio:
                try:
                    self.socketio.emit('strategy_signal', {
                        "user_id": uid,
                        "symbol": symbol,
                        "name": tick.get("name", ""),
                        "strategy": strategy_name,
                        "signal_type": signal_type,
                        "action": action,
                        "price": price,
                        "reason": reason,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })
                except Exception:
                    pass

            self._stats["signals"] += 1

    def _load_user_strategies(self, symbol: str) -> list:
        """加载所有关联该股票的用户策略配置"""
        try:
            conn = sqlite3.connect(cfg.data_dir + "/users.db")
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT user_id, name, is_active FROM strategy_configs WHERE is_active=1"
            ).fetchall()
            conn.close()
            return [{"user_id": r["user_id"], "name": r["name"]} for r in rows]
        except Exception:
            return []

    def _save_signal(self, user_id: int, symbol: str, name: str,
                     action: str, price: float, reason: str):
        """保存信号到 user_trade_logs"""
        try:
            conn = sqlite3.connect(cfg.data_dir + "/users.db")
            conn.execute(
                """INSERT INTO user_trade_logs (user_id, symbol, name, market, action, score, price, reason, created_at)
                   VALUES (?,?,?,'A股',?,?,?,?,?)""",
                (user_id, symbol, name, action, 50, price, reason, _utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"保存信号失败: {e}")

    @property
    def stats(self):
        return dict(self._stats)

    def shutdown(self):
        self._executor.shutdown(wait=False)
