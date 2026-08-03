"""
认证核心逻辑

- JWT 令牌生成 & 校验
- bcrypt 密码哈希 & 验证
- 密码强度校验
- Flask token_required 装饰器
"""

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from functools import wraps

import bcrypt
import jwt
from flask import g, jsonify, request

from src.lxl_quantaxis.core.security.rate_limit import InMemoryRateLimiter
from src.lxl_quantaxis.core.security.settings import (
    SecurityConfigurationError,
    SecuritySettings,
)

# ═══════════════════════════════════════════════════════════
# JWT 配置
# ═══════════════════════════════════════════════════════════

SECURITY_SETTINGS = SecuritySettings.from_env()
_SECRET_KEY = SECURITY_SETTINGS.jwt_secret
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = SECURITY_SETTINGS.access_token_expire_hours
_AUTH_RATE_LIMITER = InMemoryRateLimiter()


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
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError("user_id must be a positive integer")

    now = datetime.now(UTC)
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
    return jwt.decode(
        token,
        _SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["user_id", "iat", "exp"]},
    )


def auth_rate_limited(scope: str):
    """Limit public authentication endpoints by address and username."""
    if not scope:
        raise ValueError("scope cannot be empty")

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            payload = request.get_json(silent=True) or {}
            username = str(payload.get("username", "")).strip().lower()
            remote_address = request.remote_addr or "unknown"
            key = f"{scope}:{remote_address}:{username}"
            decision = _AUTH_RATE_LIMITER.check(
                key,
                limit=SECURITY_SETTINGS.auth_rate_limit_attempts,
                window_seconds=SECURITY_SETTINGS.auth_rate_limit_window_seconds,
            )
            if not decision.allowed:
                response = jsonify({"error": "请求过于频繁，请稍后重试"})
                response.headers["Retry-After"] = str(decision.retry_after_seconds)
                return response, 429
            return f(*args, **kwargs)

        return decorated

    return decorator


# ═══════════════════════════════════════════════════════════
# Flask 装饰器
# ═══════════════════════════════════════════════════════════


def _authenticate_request(required_role: str | None = None):
    auth_header = request.headers.get("Authorization", "")
    scheme, separator, token = auth_header.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        return jsonify({"error": "缺少认证令牌，请先登录"}), 401

    try:
        payload = _decode_token(token.strip())
        user_id = payload["user_id"]
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            raise jwt.InvalidTokenError("invalid user_id claim")
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "登录已过期，请重新登录"}), 401
    except (jwt.InvalidTokenError, KeyError, TypeError):
        return jsonify({"error": "令牌无效，请重新登录"}), 401

    from src.database import SessionLocal
    from src.database.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user or not user.is_active:
            return jsonify({"error": "账户不存在或已被禁用"}), 401
        if required_role and user.role != required_role:
            return jsonify({"error": "需要管理员权限"}), 403
        g.user_id = user.id
        g.user_role = user.role
    except Exception:
        return jsonify({"error": "认证服务暂时不可用"}), 503
    finally:
        db.close()

    return None


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
        error_response = _authenticate_request()
        if error_response is not None:
            return error_response
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
        error_response = _authenticate_request(required_role="admin")
        if error_response is not None:
            return error_response
        return f(*args, **kwargs)

    return decorated


def create_admin_if_not_exists(
    session_factory=None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """
    确保系统中至少有一个管理员账号。

    仅在系统不存在管理员、且显式提供 ADMIN_PASSWORD 时创建。
    生产环境缺少引导密码会终止启动；任何日志都不会输出密码。
    """
    settings = SecuritySettings.from_env(environ)
    source = os.environ if environ is None else environ
    if session_factory is None:
        from src.database import SessionLocal

        session_factory = SessionLocal
    from src.database.models import User

    db = session_factory()
    try:
        existing_admin = db.query(User).filter_by(role="admin").first()
        if existing_admin:
            return False

        admin_password = source.get("ADMIN_PASSWORD", "")
        if not admin_password:
            message = "ADMIN_PASSWORD is required for the one-time administrator bootstrap"
            if settings.is_production:
                raise SecurityConfigurationError(message)
            print(f"[Auth] {message}; no administrator was created")
            return False

        valid, validation_message = validate_password_strength(admin_password)
        if not valid or len(admin_password) < 12:
            raise SecurityConfigurationError(
                f"ADMIN_PASSWORD must be at least 12 characters and contain letters and numbers ({validation_message})"
            )

        admin_username = source.get("ADMIN_USERNAME", "admin").strip()
        if len(admin_username) < 2:
            raise SecurityConfigurationError("ADMIN_USERNAME must contain at least 2 characters")
        username_collision = db.query(User).filter_by(username=admin_username).first()
        if username_collision:
            raise SecurityConfigurationError("ADMIN_USERNAME already belongs to a non-admin account")

        admin = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            email=source.get("ADMIN_EMAIL", "admin@quantaxis.local").strip(),
            role="admin",
        )
        db.add(admin)
        db.commit()
        print(f"[Auth] 管理员账号已创建: {admin_username}")
        return True
    except Exception:
        db.rollback()
        raise
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
            raise SessionExpired("Token 已过期，回测任务中断") from None
        except jwt.InvalidTokenError:
            raise SessionExpired("Token 无效，回测任务中断") from None

    return check
