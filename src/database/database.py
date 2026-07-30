"""
数据库模块别名

从 __init__.py 重新导出所有内容，兼容 import src.database.database 路径。
"""
from src.database import (
    Base, engine, SessionLocal, get_db, init_db, DATABASE_URL,
)
from src.database.models import User, Portfolio, StrategyConfig

__all__ = [
    "Base", "engine", "SessionLocal", "get_db", "init_db",
    "DATABASE_URL", "User", "Portfolio", "StrategyConfig",
]