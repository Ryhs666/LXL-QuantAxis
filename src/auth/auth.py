"""
认证核心逻辑

- JWT 令牌生成 & 校验
- bcrypt 密码哈希 & 验证
- 密码强度校验
- Flask token_required 装饰器
"""

import os
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import bcrypt
from flask import request, jsonify, g


# ═══════════════════════════════════════════════════════════
# JWT 配置
# ═══════════════════════════════════════════════════════════

# 优先从环境变量读取，否则用基于机器特征生成的 key
_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not _SECRET_KEY:
    # 用项目路径 + 固定盐值生成确定性 secret（不同机器不同密钥）
    _machine_id = os.path.abspath(__file__).encode()
    _SECRET_KEY = hashlib.sha256(
        _machine_id + b"quantaxis-jwt-salt-2024"
    ).hexdigest()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# ═══════════════════════════════════════════════════════════
# 密码安全
# ═══════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """
    对明文密码进行 bcrypt 哈希。

    参数:
        password: 明文密码（UTF-8 编码）

    返回:
        bcrypt hash 字符串（含 salt，可直接存入数据库）
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码是否匹配。

    参数:
        password: 用户输入的明文密码
        hashed: 数据库中存储的 bcrypt hash

    返回:
        True 表示密码正确
    """
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError, AttributeError):
        # hash 格式无效
        return False


def validate_password_strength(password: str) -> tuple:
    """
    校验密码强度。

    规则:
        - 最少 8 位字符
        - 必须同时包含字母和数字

    返回:
        (is_valid: bool, message: str)
    """
    if len(password) < 8:
        return False, "密码至少需要 8 位字符"

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not has_letter or not has_digit:
        return False, "密码必须同时包含字母和数字"

    return True, "密码强度合格"


# ═══════════════════════════════════════════════════════════
# JWT 令牌
# ═══════════════════════════════════════════════════════════

def generate_token(user_id: int) -> str:
    """
    生成 JWT access token。

    参数:
        user_id: 用户 ID

    返回:
        JWT 字符串（有效期 24 小时）
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """
    解析并验证 JWT token，返回 payload。

    抛出:
        jwt.ExpiredSignatureError — token 过期
        jwt.InvalidTokenError — token 无效
    """
    return jwt.decode(token, _SECRET_KEY, algorithms=[JWT_ALGORITHM])


# ═══════════════════════════════════════════════════════════
# Flask 装饰器
# ═══════════════════════════════════════════════════════════

def token_required(f):
    """
    Flask 路由装饰器 — 要求请求携带有效的 Bearer token。

    用法:
        @app.route('/api/me')
        @token_required
        def api_me():
            user_id = g.user_id
            ...

    验证通过后，g.user_id 被设置为当前用户的 ID。
    验证失败返回 401 JSON 错误。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从 Authorization header 提取 Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            return jsonify({"error": "缺少认证令牌，请先登录"}), 401

        try:
            payload = _decode_token(token)
            g.user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "登录已过期，请重新登录"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "令牌无效，请重新登录"}), 401

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    Flask 路由装饰器 — 要求请求者是超级管理员。

    先验证 token_required，再检查 role == 'admin'。
    非管理员返回 403。

    用法:
        @app.route('/api/admin/users')
        @admin_required
        def api_admin_users():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 先验证 token
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            return jsonify({"error": "缺少认证令牌"}), 401

        try:
            payload = _decode_token(token)
            user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "登录已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "令牌无效"}), 401

        # 检查管理员角色
        from src.database import SessionLocal
        from src.database.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter_by(id=user_id).first()
            if not user or user.role != "admin":
                return jsonify({"error": "需要管理员权限"}), 403
            g.user_id = user_id
            g.user_role = user.role
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated


def create_admin_if_not_exists():
    """
    确保系统中至少有一个管理员账号。

    用户名: admin
    密码: 从环境变量 ADMIN_PASSWORD 读取，默认 admin123456

    仅在 users 表中不存在 admin 用户时创建。
    首次登录后请立即修改密码。
    """
    import os as _os
    from src.database import SessionLocal
    from src.database.models import User

    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(username="admin").first()
        if existing:
            # 确保角色是 admin
            if existing.role != "admin":
                existing.role = "admin"
                db.commit()
            return

        admin_password = _os.environ.get("ADMIN_PASSWORD", "admin123456")
        from src.auth import hash_password

        admin = User(
            username="admin",
            password_hash=hash_password(admin_password),
            email="admin@quantaxis.local",
            role="admin",
        )
        db.add(admin)
        db.commit()
        print(f"[Auth] 管理员账号已创建: admin / {admin_password}")
    except Exception as e:
        db.rollback()
        print(f"[Auth] 创建管理员失败: {e}")
    finally:
        db.close()


class SessionExpired(Exception):
    """Token 过期异常 — 用于中断正在执行的异步任务 (陷阱4)"""
    pass


def create_token_checker(token: str):
    """
    创建一个 token 有效性检查函数。

    用于长时间运行的任务（如回测）中定期检查 token 是否仍有效。
    如果 token 过期或无效，抛出 SessionExpired 异常以中断计算。

    用法:
        checker = create_token_checker(token)
        BacktestEngine(token_validator=checker).run(...)
    """
    def check():
        try:
            _decode_token(token)
        except jwt.ExpiredSignatureError:
            raise SessionExpired("Token 已过期，回测任务中断")
        except jwt.InvalidTokenError:
            raise SessionExpired("Token 无效，回测任务中断")
    return check
