"""
SQLAlchemy 数据模型

三个模型:
    User             — 用户账户（登录/注册）
    Portfolio        — 用户持仓记录
    StrategyConfig   — 用户策略配置
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.database import Base


def _utcnow():
    """返回当前 UTC 时间（naive datetime，SQLite 兼容）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(128), default="")
    role = Column(String(16), default="user")  # "user" / "admin"
    created_at = Column(DateTime, default=_utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # 关系
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    strategy_configs = relationship("StrategyConfig", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        """转为字典（不含密码哈希）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email or "",
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M") if self.last_login else "",
            "is_active": self.is_active,
        }


class Portfolio(Base):
    """用户持仓表"""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(16), nullable=False)
    name = Column(String(64), default="")
    market = Column(String(8), default="A股")
    quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    user = relationship("User", back_populates="portfolios")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else "",
        }


class StrategyConfig(Base):
    """用户策略配置表"""

    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    config_json = Column(Text, default="{}")
    strategy_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    user = relationship("User", back_populates="strategy_configs")

    is_active = Column(Boolean, default=True)

    # 每个用户的策略名唯一
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_strategy_name"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "config_json": self.config_json,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else "",
            "is_active": self.is_active,
        }


class UserTradeLog(Base):
    """用户交易建议日志表 — 每日扫描/诊断结果存档"""

    __tablename__ = "user_trade_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(16), nullable=False)
    name = Column(String(64), default="")
    market = Column(String(8), default="A股")
    action = Column(String(8), nullable=False)
    score = Column(Integer, default=50)
    price = Column(Float, default=0.0)
    reason = Column(String(256), default="")
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "action": self.action,
            "score": self.score,
            "price": self.price,
            "reason": self.reason,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }
