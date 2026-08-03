"""
数据库引擎 & 会话管理 (SQLAlchemy)

默认使用 DataRoot 下的 SQLite users.db，后续可无缝迁移至 MySQL/PostgreSQL。
更换数据库只需修改 DATABASE_URL 即可，无需改动任何业务代码。
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.lxl_quantaxis.data.storage import DataRoot, LegacySqliteAdapter

# 数据库文件路径（SQLite），可从环境变量覆盖
_DATA_ROOT = DataRoot.from_sources()
_SQLITE_ADAPTER = LegacySqliteAdapter(_DATA_ROOT)
DATABASE_PATH: Path | None = _SQLITE_ADAPTER.preferred_path("users.db")
DATABASE_URL = os.environ.get(
    "QUANT_DATABASE_URL",
    f"sqlite:///{DATABASE_PATH.as_posix()}",
)
if "QUANT_DATABASE_URL" in os.environ:
    DATABASE_PATH = None

# SQLite 需要 check_same_thread=False 以支持多线程
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,           # 生产环境关闭 SQL 日志
    pool_pre_ping=True,   # 连接池健康检查
)

# 会话工厂 — 每个请求创建一个 Session 实例
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 模型基类
Base = declarative_base()


def get_db():
    """
    Flask 请求生命周期使用的数据库会话生成器。

    用法:
        @app.route('/api/example')
        def example():
            db = next(get_db())
            try:
                user = db.query(User).filter_by(id=1).first()
                return jsonify({"username": user.username})
            finally:
                db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> bool:
    """
    创建所有表，并在显式配置引导密码时创建首个管理员。

    返回 True 表示本次创建了管理员。生产环境配置不安全时抛出异常，
    不会使用默认密码继续启动。

    用法:
        from src.database import init_db
        init_db()
    """
    # 显式初始化时才创建数据目录；导入模块不会写磁盘。
    if DATABASE_PATH is not None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 创建所有模型对应的表
    from src.database import models  # noqa: F401 — 触发模型注册
    Base.metadata.create_all(bind=engine)
    # 确保管理员账号存在
    from src.auth import create_admin_if_not_exists
    return create_admin_if_not_exists()
