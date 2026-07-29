"""
量化系统日志 + 工具集

- 结构化日志（文件 + 控制台）
- 重试装饰器
- 进度条封装
- 时间/编码工具
"""

import sys
import os
import time
import logging
import functools
from datetime import datetime
from pathlib import Path

from src.config import config

# ---- Windows 编码 ----
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 日志系统
# ============================================================

_logger = None


def get_logger(name: str = "quant") -> logging.Logger:
    """获取全局 logger"""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # 避免重复 handler
    if _logger.handlers:
        return _logger

    # 格式
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 handler
    os.makedirs(config.log_dir, exist_ok=True)
    log_file = os.path.join(config.log_dir, f"quant_{datetime.now().strftime('%Y%m%d')}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    # 控制台 handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    _logger.addHandler(ch)

    return _logger


logger = get_logger()


# ============================================================
# 重试装饰器
# ============================================================

def retry(max_attempts: int = 3, delay: float = 2.0,
          backoff: float = 2.0, exceptions=(Exception,),
          on_retry=None):
    """
    重试装饰器

    用法:
        @retry(max_attempts=5, delay=1.0, exceptions=(ConnectionError,))
        def fetch_data():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} 第 {attempt} 次失败: {e}，"
                            f"{current_delay:.1f}s 后重试..."
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {max_attempts} 次全部失败: {e}"
                        )

            raise last_error
        return wrapper
    return decorator


# ============================================================
# 进度条
# ============================================================

class ProgressBar:
    """简易进度条（不依赖 tqdm）"""

    def __init__(self, total: int, desc: str = "", width: int = 40,
                 verbose: bool = True):
        self.total = max(1, total)
        self.current = 0
        self.desc = desc
        self.width = width
        self.verbose = verbose
        self.start_time = time.time()
        self._last_len = 0

    def update(self, n: int = 1, extra: str = ""):
        self.current = min(self.current + n, self.total)
        if not self.verbose:
            return

        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)

        elapsed = time.time() - self.start_time
        if pct > 0:
            eta = elapsed / pct * (1 - pct)
            eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta / 60:.1f}min"
        else:
            eta_str = "..."

        msg = f"\r  {self.desc} |{bar}| {self.current}/{self.total} ({pct*100:.0f}%) "
        msg += f"[{elapsed:.0f}s<{eta_str}]"
        if extra:
            msg += f" {extra}"

        # 清除之前的输出
        if self._last_len > len(msg):
            msg += " " * (self._last_len - len(msg))
        self._last_len = len(msg)

        sys.stdout.write(msg)
        sys.stdout.flush()

    def close(self):
        if self.verbose:
            elapsed = time.time() - self.start_time
            print(f"\n  ✅ 完成！共 {self.current} 项，耗时 {elapsed:.1f}s")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ============================================================
# 计时器
# ============================================================

class Timer:
    """上下文计时器"""
    def __init__(self, label: str = "", verbose: bool = True):
        self.label = label
        self.verbose = verbose
        self.start = 0
        self.elapsed = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start
        if self.verbose:
            if self.elapsed < 1:
                t = f"{self.elapsed * 1000:.0f}ms"
            elif self.elapsed < 60:
                t = f"{self.elapsed:.1f}s"
            else:
                t = f"{self.elapsed / 60:.1f}min"
            label_str = f" [{self.label}]" if self.label else ""
            print(f"  ⏱️ 耗时{label_str}: {t}")


# ============================================================
# 安全执行
# ============================================================

def safe_call(func, *args, default=None, log_error: bool = True, **kwargs):
    """
    安全调用函数，不抛异常

    返回: (result, error_string) 或 (default, error_string)
    """
    try:
        return func(*args, **kwargs), None
    except Exception as e:
        if log_error:
            logger.error(f"{func.__name__} 执行失败: {e}")
        return default, str(e)


# ============================================================
# 文件工具
# ============================================================

def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def timestamp() -> str:
    """返回时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
