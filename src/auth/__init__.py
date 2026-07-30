"""
认证模块

JWT 鉴权 + bcrypt 密码加密 + token_required 装饰器

用法:
    from src.auth import token_required, hash_password, verify_password, generate_token
    from src.auth.auth import validate_password_strength
"""

from src.auth.auth import (
    generate_token,
    token_required,
    admin_required,
    hash_password,
    verify_password,
    validate_password_strength,
    create_admin_if_not_exists,
)

__all__ = [
    "generate_token",
    "token_required",
    "admin_required",
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "create_admin_if_not_exists",
]
