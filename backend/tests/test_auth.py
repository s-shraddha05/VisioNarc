from datetime import timedelta

from sqlalchemy import select

from app.core.security import create_access_token
from app.db.base import utcnow
from app.models import AdminSession, AuditLog
from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME, login


def actions(db) -> list[str]:
    db.expire_all()
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.id)))


def test_login_success_returns_token_and_profile(client, admin, db):
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["admin"]["username"] == TEST_ADMIN_USERNAME
    assert "password_hash" not in body["admin"]
    assert body["expires_at"].endswith("Z") or body["expires_at"].endswith("+00:00")
    assert "auth.login" in actions(db)


def test_login_username_is_case_insensitive(client, admin):
    assert login(client, username="  TestAdmin ").status_code == 200


def test_wrong_password_and_unknown_user_look_identical(client, admin, db):
    wrong = login(client, password="Wrong-Password-1")
    unknown = login(client, username="nobody")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert actions(db).count("auth.login_failed") == 2


def test_login_validation_error(client):
    assert client.post("/api/v1/auth/login", json={"username": ""}).status_code == 422


def test_account_locks_after_max_failures(client, admin, db, settings):
    for _ in range(settings.login_max_failed_attempts):
        assert login(client, password="Wrong-Password-1").status_code == 401
    # Correct password is refused while locked.
    assert login(client).status_code == 401
    assert "auth.account_locked" in actions(db)

    db.expire_all()
    admin.locked_until = utcnow() - timedelta(seconds=1)
    db.merge(admin)
    db.commit()
    assert login(client).status_code == 200


def test_me_requires_valid_token(client, auth_headers):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == TEST_ADMIN_USERNAME


def test_tampered_token_rejected(client, auth_headers):
    token = auth_headers["Authorization"].split()[1]
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_token_without_session_row_rejected(client, admin, settings):
    # Correctly signed but never issued by /login (no admin_sessions row).
    token, _, _ = create_access_token(admin.id, settings)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_expired_session_rejected(client, auth_headers, db):
    db.expire_all()
    session = db.scalars(select(AdminSession)).one()
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401


def test_logout_revokes_token(client, auth_headers, db):
    assert client.post("/api/v1/auth/logout", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401
    assert client.post("/api/v1/auth/logout", headers=auth_headers).status_code == 401
    assert "auth.logout" in actions(db)


def test_inactive_admin_cannot_use_existing_token(client, auth_headers, admin, db):
    db.expire_all()
    admin.is_active = False
    db.merge(admin)
    db.commit()
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401
    assert login(client).status_code == 401


def test_change_password_flow(client, auth_headers, db):
    other_device = {"Authorization": f"Bearer {login(client).json()['access_token']}"}
    new_password = "Brand-New-Password-7"

    bad_current = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "nope-nope-123", "new_password": new_password},
    )
    assert bad_current.status_code == 400

    weak = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": TEST_ADMIN_PASSWORD, "new_password": "weak"},
    )
    assert weak.status_code == 422

    ok = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": TEST_ADMIN_PASSWORD, "new_password": new_password},
    )
    assert ok.status_code == 200
    # The session that changed the password stays valid; other sessions are revoked.
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=other_device).status_code == 401
    assert login(client).status_code == 401
    assert login(client, password=new_password).status_code == 200
    assert "auth.password_changed" in actions(db)


def test_security_headers_present(client):
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
