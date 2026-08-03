"""
认证模块

JWT 鉴权 + bcrypt 密码加密 + token_required 装饰器

用法:
    from src.auth import token_required, hash_password, verify_password, generate_token
    from src.auth.auth import validate_password_strength
"""

from src.auth.auth import (
    SECURITY_SETTINGS,
    admin_required,
    auth_rate_limited,
    create_admin_if_not_exists,
    generate_token,
    hash_password,
    token_required,
    validate_password_strength,
    verify_password,
)

__all__ = [
    "SECURITY_SETTINGS",
    "admin_required",
    "auth_rate_limited",
    "create_admin_if_not_exists",
    "generate_token",
    "hash_password",
    "token_required",
    "validate_password_strength",
    "verify_password",
]
