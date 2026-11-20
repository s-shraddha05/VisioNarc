from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    normalize_username,
    validate_password_strength,
    validate_username,
    verify_password,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("Correct-Horse-42", rounds=4)
    assert hashed.startswith("$2b$")
    assert "Correct-Horse-42" not in hashed
    assert verify_password("Correct-Horse-42", hashed)
    assert not verify_password("correct-horse-42", hashed)


def test_hash_rejects_passwords_over_72_bytes():
    with pytest.raises(ValueError):
        hash_password("a1" * 40, rounds=4)


def test_verify_never_raises_on_bad_input():
    assert not verify_password("x" * 100, hash_password("Short-pass-123", rounds=4))
    assert not verify_password("anything", "not-a-bcrypt-hash")


@pytest.mark.parametrize(
    "password, ok",
    [
        ("Long-Enough-123", True),
        ("short1A", False),
        ("onlyletterslong", False),
        ("123456789012345", False),
        (" Leading-space-123", False),
        ("é" * 37 + "1", False),  # 75 bytes
    ],
)
def test_password_strength(password, ok):
    assert (validate_password_strength(password) == []) is ok


def test_username_rules():
    assert normalize_username("  Admin ") == "admin"
    assert validate_username("admin") == []
    assert validate_username("ab") != []
    assert validate_username("bad name") != []


def test_token_roundtrip(settings):
    token, jti, expires_at = create_access_token(7, settings)
    payload = decode_access_token(token, settings)
    assert payload["sub"] == "7"
    assert payload["jti"] == jti
    assert expires_at.tzinfo is None


def test_token_rejects_wrong_secret_and_expiry(settings):
    token, _, _ = create_access_token(1, settings)
    other = settings.model_copy(update={"jwt_secret_key": "another-secret-key-that-is-long-enough!!"})
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, other)

    past = datetime.now(UTC) - timedelta(hours=2)
    expired = jwt.encode(
        {"sub": "1", "jti": "x", "iss": settings.jwt_issuer, "iat": past, "exp": past + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired, settings)


def test_startup_rejects_weak_secret(settings):
    with pytest.raises(RuntimeError):
        settings.model_copy(update={"jwt_secret_key": "short"}).validate_for_startup()
    with pytest.raises(RuntimeError):
        settings.model_copy(
            update={"jwt_secret_key": "replace-with-a-long-random-secret"}
        ).validate_for_startup()
