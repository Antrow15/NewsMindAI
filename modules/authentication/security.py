"""Password hashing (stdlib) + JWT access tokens (PyJWT)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from config.constants import (
    JWT_ALGORITHM,
    PASSWORD_HASH_ITERATIONS,
    PASSWORD_SALT_BYTES,
    SESSION_TTL_HOURS,
    get_jwt_secret,
)


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Return stored form: salt_hex$digest_hex (single ERD password_hash field)."""
    if not password:
        raise ValueError("Password must not be empty")
    salt_bytes = salt if salt is not None else os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, digest_hex = password_hash.split("$", 1)
        candidate = hash_password(password, salt=bytes.fromhex(salt_hex))
        return hmac.compare_digest(candidate, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: int, username: str, role_code: str = "") -> str:
    """Create a signed JWT access token (HS256)."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_id": int(user_id),
        "username": username,
        "role_code": role_code or "",
        "iat": now,
        "exp": now + timedelta(hours=SESSION_TTL_HOURS),
        "jti": secrets.token_urlsafe(16),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )
