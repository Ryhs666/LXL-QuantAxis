# -*- coding: utf-8 -*-
"""
Alert Engine — 实时监控与告警引擎

规则驱动 + 多渠道通知 (邮件/钉钉/微信/Telegram/控制台)。
支持 YAML 配置文件加载规则。

集成方式:
    from src.realtime.alert_engine import alert_engine
    alert_engine.start()
    # 在行情回调中:
    alert_engine.check({"symbol": "600519", "price": 2010.0, "volume": 50000})
"""

import json
import os
import smtplib
import time
import threading
import queue
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.header import Header
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("realtime.alert")


# ═══════════════════════════════════════════
# 枚举 & 数据结构
# ═══════════════════════════════════════════

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    rule_id: str
    name: str
    condition: Callable[[Dict], bool]
    level: AlertLevel = AlertLevel.WARNING
    message_template: str = ""
    enabled: bool = True
    cooldown_seconds: int = 60
    last_triggered: Optional[float] = None

    def is_ready(self) -> bool:
        if self.last_triggered is None:
            return True
        return (time.time() - self.last_triggered) >= self.cooldown_seconds

    def trigger(self, context: Dict[str, Any]) -> str:
        self.last_triggered = time.time()
        try:
            return self.message_template.format(**context)
        except KeyError:
            return f"[{self.name}] {context}"


# ═══════════════════════════════════════════
# 通知渠道
# ═══════════════════════════════════════════

class NotificationChannel(ABC):
    @abstractmethod
    def send(self, title: str, message: str, level: AlertLevel) -> bool: ...


class ConsoleChannel(NotificationChannel):
    def send(self, title: str, message: str, level: AlertLevel) -> bool:
        print(f"[{level.value.upper()}] {title}: {message}")
        return True


class EmailChannel(NotificationChannel):
    def __init__(self, host: str, port: int, sender: str, password: str, receivers: List[str]):
        self.host, self.port, self.sender, self.password, self.receivers = \
            host, port, sender, password, receivers

    def send(self, title: str, message: str, level: AlertLevel) -> bool:
        try:
            msg = MIMEText(message, 'plain', 'utf-8')
            msg['Subject'] = Header(f"[LXL] {title}", 'utf-8')
            msg['From'], msg['To'] = self.sender, ', '.join(self.receivers)
            server = smtplib.SMTP_SSL(self.host, self.port)
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receivers, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """通用 Webhook — 钉钉/企业微信/飞书"""
    def __init__(self, url: str, secret: str = None, platform: str = "dingtalk"):
        self.url, self.secret, self.platform = url, secret, platform

    def send(self, title: str, message: str, level: AlertLevel) -> bool:
        try:
            import requests
            text = f"【{level.value.upper()}】{title}\n{message}"
            data = {"msgtype": "text", "text": {"content": text}}
            if self.platform == "feishu":
                data = {"msg_type": "text", "content": {"text": text}}
            resp = requests.post(self.url, json=data, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Webhook 发送失败: {e}")
            return False


# ═══════════════════════════════════════════
# 告警引擎
# ═══════════════════════════════════════════

class AlertEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init = False
        return cls._instance

    def __init__(self):
        if self._init: return
        self._init = True
        self.rules: Dict[str, AlertRule] = {}
        self.channels: List[NotificationChannel] = [ConsoleChannel()]
        self._queue = queue.Queue()
        self._running = False
        self._thread = None

    def add_rule(self, rule: AlertRule):
        self.rules[rule.rule_id] = rule

    def add_channel(self, channel: NotificationChannel):
        self.channels.append(channel)

    def check(self, context: Dict[str, Any]):
        for rule in self.rules.values():
            if not rule.enabled or not rule.is_ready():
                continue
            try:
                if rule.condition(context):
                    msg = rule.trigger(context)
                    self._queue.put((rule, msg))
            except Exception as e:
                logger.error(f"规则 {rule.rule_id} 异常: {e}")

    def _process_queue(self):
        while self._running:
            try:
                rule, msg = self._queue.get(timeout=1)
                title = f"{rule.name}"
                for ch in self.channels:
                    try: ch.send(title, msg, rule.level)
                    except Exception: pass
            except queue.Empty: pass

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── YAML 配置加载 ──
    def load_rules_from_yaml(self, path: str = None):
        """从 config/alerts.yaml 加载告警规则"""
        path = path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", "alerts.yaml"
        )
        if not os.path.exists(path):
            logger.info(f"告警配置文件不存在: {path}, 使用默认规则")
            self._add_default_rules()
            return

        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception:
            # 尝试 JSON
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"告警配置加载失败: {e}")
                self._add_default_rules()
                return

        if not config:
            return

        # 加载渠道
        for ch_cfg in config.get("channels", []):
            ch_type = ch_cfg.get("type", "")
            if ch_type == "console":
                pass  # 默认已有
            elif ch_type == "email":
                self.add_channel(EmailChannel(
                    ch_cfg["host"], ch_cfg.get("port", 465),
                    ch_cfg["sender"], ch_cfg["password"],
                    ch_cfg.get("receivers", []),
                ))
            elif ch_type in ("dingtalk", "wechat", "feishu"):
                self.add_channel(WebhookChannel(
                    ch_cfg["url"], ch_cfg.get("secret"),
                    platform=ch_type,
                ))

        # 加载规则
        for r_cfg in config.get("rules", []):
            try:
                rule = self._build_rule_from_config(r_cfg)
                if rule:
                    self.add_rule(rule)
            except Exception as e:
                logger.warning(f"规则加载失败: {r_cfg.get('id', '?')} — {e}")

        logger.info(f"已加载 {len(self.rules)} 条告警规则")

    def _build_rule_from_config(self, cfg: dict) -> Optional[AlertRule]:
        """从配置字典构建规则"""
        rule_type = cfg.get("type", "")
        rid = cfg.get("id", cfg.get("rule_id", ""))

        if rule_type == "price_breakout":
            symbol = cfg["symbol"]
            threshold = float(cfg["threshold"])
            direction = cfg.get("direction", "above")
            def cond(ctx, s=symbol, t=threshold, d=direction):
                if ctx.get("symbol") != s: return False
                p = ctx.get("price", 0)
                return p >= t if d == "above" else p <= t
            return AlertRule(
                rule_id=rid, name=f"价格突破 {symbol} {direction} {threshold}",
                condition=cond, level=AlertLevel(cfg.get("level", "warning")),
                message_template=cfg.get("message", f"{symbol} 价格突破 {threshold}, 当前: {{price}}"),
                cooldown_seconds=cfg.get("cooldown", 300),
            )

        elif rule_type == "volume_spike":
            symbol = cfg["symbol"]
            multiplier = float(cfg.get("multiplier", 2.0))
            lookback = int(cfg.get("lookback", 20))
            history = []
            def cond(ctx, s=symbol, m=multiplier, lb=lookback, h=history):
                if ctx.get("symbol") != s: return False
                v = ctx.get("volume", 0)
                if v <= 0: return False
                h.append(v)
                if len(h) > lb * 2: h.pop(0)
                if len(h) < lb: return False
                avg = sum(h[-lb:]) / lb
                return v >= avg * m
            return AlertRule(
                rule_id=rid, name=f"成交量异动 {symbol} x{multiplier}",
                condition=cond, level=AlertLevel(cfg.get("level", "info")),
                message_template=cfg.get("message", f"{symbol} 放量 x{multiplier}"),
                cooldown_seconds=cfg.get("cooldown", 600),
            )

        elif rule_type == "drawdown":
            threshold = float(cfg.get("threshold", 0.10))
            def cond(ctx, t=threshold):
                dd = ctx.get("drawdown_pct", 0)
                return dd >= t
            return AlertRule(
                rule_id=rid, name=f"回撤告警 >{threshold:.0%}",
                condition=cond, level=AlertLevel.ERROR,
                message_template=f"账户回撤超过 {threshold:.0%}! 当前回撤: {{drawdown_pct:.1%}}",
                cooldown_seconds=cfg.get("cooldown", 900),
            )

        return None

    def _add_default_rules(self):
        """添加默认规则 (无 YAML 配置文件时)"""
        def drawdown_cond(ctx):
            return ctx.get("drawdown_pct", 0) >= 0.10
        self.add_rule(AlertRule(
            rule_id="default_drawdown", name="回撤告警 (>10%)",
            condition=drawdown_cond, level=AlertLevel.ERROR,
            message_template="账户回撤超过10%! 当前回撤: {drawdown_pct:.1%}",
            cooldown_seconds=900,
        ))


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

alert_engine = AlertEngine()
