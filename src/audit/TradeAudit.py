"""
TradeAudit — 交易日志审计模块 (v6.1)

1. 记录每次交易决策到 D:/trading_data/logs/audit.log (微秒时间戳)
2. 异常检测: 连续失败3次或日跌幅>5%时桌面弹窗告警
"""

import logging
import os
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════

LOG_DIR = "D:/trading_data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 审计日志 — 微秒精度
_audit_logger = logging.getLogger("TradeAudit")
_audit_logger.setLevel(logging.DEBUG)
_audit_handler = logging.FileHandler(
    os.path.join(LOG_DIR, "audit.log"), encoding="utf-8")
_audit_handler.setFormatter(logging.Formatter(
    "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"))
_audit_logger.addHandler(_audit_handler)


class TradeAudit:
    """交易审计追踪器"""

    def __init__(self):
        self.consecutive_failures = 0
        self.max_failures = 3
        self.daily_drawdown_threshold = 0.05  # 5%
        self._last_equity = None
        self._start_of_day_equity = None
        self._today = None

    # ═══════════════════════════════════════════
    # 1. 交易记录
    # ═══════════════════════════════════════════

    def log_decision(self, action: str, symbol: str, price: float,
                     quantity: int = 0, strategy: str = "",
                     ai_advice: str = "", reason: str = "",
                     portfolio_value: float = 0):
        """
        记录一次交易决策
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 重置每日状态
        if self._today != today:
            self._today = today
            self._start_of_day_equity = portfolio_value if portfolio_value > 0 else None

        # 构建日志
        parts = [
            f"symbol={symbol}",
            f"action={action}",
            f"price={price:.2f}",
            f"qty={quantity}",
            f"strategy={strategy or 'manual'}",
        ]
        if ai_advice:
            parts.append(f"ai_advice={ai_advice[:80]}")
        if reason:
            parts.append(f"reason={reason[:100]}")
        parts.append(f"equity={portfolio_value:,.0f}")

        _audit_logger.info(" | ".join(parts))

        # 跟踪连续失败
        if action in ("SELL", "STOP") and reason and (
            "止损" in reason or "亏损" in reason or "失败" in reason
        ):
            self.consecutive_failures += 1
            _audit_logger.warning(
                f"连续失败计数: {self.consecutive_failures}/{self.max_failures}")
        elif action == "BUY":
            self.consecutive_failures = 0

        # 检查告警
        self._check_alerts(portfolio_value, today)

    def log_order(self, symbol: str, side: str, price: float, qty: int,
                  status: str = "FILLED", error: str = ""):
        """记录订单执行"""
        msg = f"ORDER | {symbol} {side} {price:.2f} x{qty} [{status}]"
        if error:
            msg += f" ERROR: {error}"
            _audit_logger.error(msg)
            self.consecutive_failures += 1
        else:
            _audit_logger.info(msg)

    def log_error(self, symbol: str, error: str):
        """记录错误"""
        _audit_logger.error(f"symbol={symbol} | {error}")
        self.consecutive_failures += 1

    def log_info(self, msg: str):
        _audit_logger.info(msg)

    # ═══════════════════════════════════════════
    # 2. 异常检测 & 告警
    # ═══════════════════════════════════════════

    def _check_alerts(self, equity: float, today: str):
        """检查是否需要告警"""
        # 检查1: 连续失败
        if self.consecutive_failures >= self.max_failures:
            self.send_alert(
                "⚠️ 交易连续失败",
                f"已连续{self.consecutive_failures}次亏损/止损\n"
                f"当前权益: ¥{equity:,.0f}\n建议暂停交易,检查策略"
            )
            self.consecutive_failures = 0  # 重置防止重复告警

        # 检查2: 日跌幅>5%
        if self._start_of_day_equity and self._start_of_day_equity > 0:
            daily_change = (equity - self._start_of_day_equity) / self._start_of_day_equity
            if daily_change < -self.daily_drawdown_threshold:
                self.send_alert(
                    "🔴 日内大幅回撤",
                    f"当日权益: ¥{equity:,.0f}\n"
                    f"开盘权益: ¥{self._start_of_day_equity:,.0f}\n"
                    f"跌幅: {daily_change*100:.1f}%\n"
                    f"请立即检查持仓!"
                )
                _audit_logger.warning(
                    f"日内回撤告警: {daily_change*100:.1f}% "
                    f"({self._start_of_day_equity:,.0f} → {equity:,.0f})"
                )

    @staticmethod
    def send_alert(title: str, message: str):
        """发送桌面弹窗 (Win10/11)"""
        _audit_logger.warning(f"ALERT | {title} | {message.replace(chr(10), '; ')}")

        # 方法1: win10toast (如果安装了)
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, message, duration=10, threaded=True)
            return
        except ImportError:
            pass

        # 方法2: Windows 原生 API (无需额外依赖)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40030)
            return
        except Exception:
            pass

        # 方法3: 写入告警文件
        alert_path = os.path.join(LOG_DIR, "alerts.log")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(alert_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {title}\n{message}\n{'='*40}\n")

    # ═══════════════════════════════════════════
    # 3. 查询
    # ═══════════════════════════════════════════

    @staticmethod
    def read_today_log() -> str:
        """读取今日日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(LOG_DIR, "audit.log")
        if not os.path.exists(log_path):
            return ""
        with open(log_path, "r", encoding="utf-8") as f:
            return "\n".join(
                line for line in f.readlines()
                if line.startswith(today) or today in line
            )

    @staticmethod
    def get_recent_errors(n: int = 20) -> list:
        """获取最近错误"""
        log_path = os.path.join(LOG_DIR, "audit.log")
        if not os.path.exists(log_path):
            return []
        errors = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if "ERROR" in line or "WARNING" in line:
                    errors.append(line.strip())
        return errors[-n:]


# 全局实例
audit = TradeAudit()
