# -*- coding: utf-8 -*-
"""
Rate Limiter — API 速率限制中间件 (内存版滑动窗口)

Flask 兼容。装饰器方式限制指定路由的单位时间请求次数。

集成方式:
    from src.utils.rate_limiter import rate_limit
    @app.route('/api/v2/trade')
    @rate_limit(max_requests=30, window_seconds=60)
    def api_trade(): ...

架构:
    MemoryRateLimiter (滑动窗口) → @rate_limit 装饰器 → Flask 路由
"""

import time
import threading
from collections import defaultdict
from functools import wraps
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("utils.rate_limiter")


class MemoryRateLimiter:
    """
    内存版滑动窗口速率限制器。

    每个 client_id 维护一个时间戳列表，窗口外旧记录自动清除。
    线程安全: 使用 threading.Lock 保护内部状态。
    """

    def __init__(self):
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(
        self, client_id: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        """
        检查是否允许请求。

        Args:
            client_id:     客户端标识 (IP 或 API Key)
            max_requests:  窗口内最大请求数
            window_seconds: 窗口大小 (秒)

        Returns:
            (是否允许, 剩余请求次数)
        """
        now = time.time()

        with self._lock:
            timestamps = self._records[client_id]

            # 清除窗口外的旧记录 (滑动窗口)
            cutoff = now - window_seconds
            valid = [t for t in timestamps if t > cutoff]
            self._records[client_id] = valid

            # 检查是否超限
            if len(valid) >= max_requests:
                # 计算下次可用时间
                oldest = valid[0] if valid else now
                wait_for = round(window_seconds - (now - oldest), 1)
                return False, 0

            # 记录本次请求
            valid.append(now)
            remaining = max_requests - len(valid)
            return True, remaining

    def reset(self, client_id: str = None):
        """重置限频记录 (None=全部)"""
        with self._lock:
            if client_id:
                self._records.pop(client_id, None)
            else:
                self._records.clear()

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "active_clients": len(self._records),
                "total_requests": sum(len(v) for v in self._records.values()),
            }


# 全局单例
_limiter = MemoryRateLimiter()


# ═══════════════════════════════════════════
# Flask 兼容装饰器
# ═══════════════════════════════════════════

def rate_limit(max_requests: int = 30, window_seconds: int = 60):
    """
    速率限制装饰器 (Flask 兼容)。

    自动从 Flask request 对象获取 client_ip。
    超限返回 HTTP 429 + JSON 错误信息。

    Args:
        max_requests:  窗口内最大请求数
        window_seconds: 窗口大小 (秒)

    Usage:
        @app.route('/api/v2/trade', methods=['POST'])
        @rate_limit(max_requests=5, window_seconds=60)
        def api_trade(): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从 Flask request 获取客户端 IP
            client_ip = _get_client_ip()

            allowed, remaining = _limiter.is_allowed(
                client_ip, max_requests, window_seconds
            )

            if not allowed:
                logger.warning(
                    f"[RateLimit] {client_ip} 超限 "
                    f"({max_requests}/{window_seconds}s)"
                )
                # 返回 Flask 兼容的 429 响应
                try:
                    from flask import jsonify
                    resp = jsonify({
                        "error": "rate_limit_exceeded",
                        "message": (
                            f"请求过于频繁, 每 {window_seconds} 秒最多 "
                            f"{max_requests} 次, 请稍后重试"
                        ),
                        "retry_after_seconds": window_seconds,
                    })
                    resp.status_code = 429
                    resp.headers["X-RateLimit-Limit"] = str(max_requests)
                    resp.headers["X-RateLimit-Remaining"] = "0"
                    resp.headers["Retry-After"] = str(window_seconds)
                    return resp
                except ImportError:
                    return "Rate limit exceeded", 429

            # 执行原函数
            result = func(*args, **kwargs)

            # 尝试在响应中注入剩余请求数
            try:
                from flask import Response
                if isinstance(result, Response):
                    result.headers["X-RateLimit-Limit"] = str(max_requests)
                    result.headers["X-RateLimit-Remaining"] = str(remaining)
                elif isinstance(result, tuple) and len(result) == 2:
                    # (body, status_code) 格式
                    pass  # 不修改 tuple
            except ImportError:
                pass

            return result

        return wrapper
    return decorator


def _get_client_ip() -> str:
    """从 Flask request 获取客户端 IP"""
    try:
        from flask import request
        # X-Forwarded-For (代理/负载均衡后)
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        # X-Real-IP
        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip:
            return real_ip.strip()
        # 直连 IP
        return request.remote_addr or "unknown"
    except Exception:
        return "unknown"


# ═══════════════════════════════════════════
# 敏感路由预定义限频配置
# ═══════════════════════════════════════════

SENSITIVE_ROUTE_LIMITS = {
    "/api/v2/trade":       (5, 60),     # 5次/分钟 — 交易
    "/api/v2/order":       (10, 60),    # 10次/分钟 — 下单
    "/api/login":          (20, 60),    # 20次/分钟 — 登录
    "/api/register":       (5, 300),    # 5次/5分钟 — 注册
    "/api/ai/chat":        (30, 60),    # 30次/分钟 — AI对话
    "/api/backtest/run":   (10, 60),    # 10次/分钟 — 回测
}


def apply_rate_limits_to_app(app, limits: dict = None):
    """
    批量为 Flask app 路由添加速率限制。

    Args:
        app:    Flask 应用实例
        limits: {route: (max_requests, window_seconds)} 或 None (使用默认)
    """
    limits = limits or SENSITIVE_ROUTE_LIMITS
    applied = 0

    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        route = rule.rule

        if route in limits:
            max_req, window = limits[route]
            view_func = app.view_functions.get(endpoint)
            if view_func:
                app.view_functions[endpoint] = rate_limit(
                    max_requests=max_req, window_seconds=window
                )(view_func)
                applied += 1
                logger.info(
                    f"[RateLimit] {route} → {max_req}/{window}s"
                )

    logger.info(f"[RateLimit] 已应用 {applied} 条限频规则")
    return applied


# ═══════════════════════════════════════════
# CLI / 测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    # 模拟被限制的函数
    @rate_limit(max_requests=3, window_seconds=10)
    def mock_api(client_ip="127.0.0.1"):
        return {"status": "ok"}

    # 此处无法模拟 Flask request, 但可以测试基础限频逻辑
    limiter = MemoryRateLimiter()
    for i in range(5):
        allowed, remaining = limiter.is_allowed("test_user", 3, 10)
        tag = "OK" if allowed else "BLOCKED"
        print(f"  请求 {i+1}: {tag} (剩余={remaining})")
        time.sleep(1)

    print(f"\n  活跃客户端: {limiter.stats['active_clients']}")
    limiter.reset()
    print("  已重置")
