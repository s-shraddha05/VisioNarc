import re
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import bcrypt
import jwt

from app.core.config import Settings

BCRYPT_MAX_BYTES = 72
PASSWORD_MIN_LENGTH = 12
USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,50}$")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> list[str]:
    if not USERNAME_PATTERN.fullmatch(username):
        return ["Username must be 3-50 characters: lowercase letters, digits, '.', '_' or '-'."]
    return []


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        errors.append(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors.append("Password must contain at least one letter and one digit.")
    if password != password.strip():
        errors.append("Password must not start or end with whitespace.")
    return errors


def hash_password(password: str, rounds: int = 12) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password exceeds {BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        # Over-long password or malformed hash: treat as a mismatch, never as an error.
        return False


@lru_cache
def _dummy_hash(rounds: int) -> str:
    return hash_password(secrets.token_urlsafe(16), rounds)


def burn_password_check(password: str, rounds: int) -> None:
    """Spend the same time as a real check so unknown usernames are not revealed by timing."""
    verify_password(password, _dummy_hash(rounds))


def create_access_token(admin_id: int, settings: Settings) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at). expires_at is naive UTC, matching DB storage."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = secrets.token_hex(16)
    payload = {
        "sub": str(admin_id),
        "jti": jti,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires.replace(tzinfo=None, microsecond=0)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Raise jwt.PyJWTError when the token is invalid, expired or tampered with."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "jti", "exp", "iat", "iss"]},
    )
