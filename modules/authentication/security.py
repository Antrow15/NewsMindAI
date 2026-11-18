"""Password hashing (stdlib). Salt embedded in password_hash (ERD has no salt column)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Tuple

from config.constants import PASSWORD_HASH_ITERATIONS, PASSWORD_SALT_BYTES


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


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
