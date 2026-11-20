"""Phase 4 security: per-IP sign-in limiting, API headers, active sign-ins, logs free of sensitive data."""

import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.services.auth_service import create_admin
from app.services.rate_limit import FailureRateLimiter
from tests.analysis_fixtures import face_payload, pose_payload, voice_wav
from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME, login
from tests.test_analysis_api import SESSIONS, new_session, post_voice

SQLALCHEMY_TIMING = re.compile(r"\[[^\]]*\d\.\d+s[^\]]*\]")


@pytest.fixture
def limited_client(settings, session_factory, admin):
    s = settings.model_copy(update={"login_ip_max_failures": 3, "login_max_failed_attempts": 50})
    app = create_app(s)

    def _get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_settings] = lambda: s
    with TestClient(app) as c:
        yield c


def test_ip_rate_limit_blocks_before_password_check(limited_client):
    for name in ("a", "b", "c"):  # spraying different usernames from one address
        assert login(limited_client, username=name, password="Wrong-Pass-123").status_code == 401
    blocked = login(limited_client)  # even the correct password
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    # Forwarded headers are not trusted to change the client address.
    spoof = limited_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.9", "X-Real-IP": "203.0.113.9"},
    )
    assert spoof.status_code == 429


def test_successful_logins_do_not_count(limited_client):
    for _ in range(5):
        assert login(limited_client).status_code == 200


def test_limiter_window_expires():
    now = [0.0]
    limiter = FailureRateLimiter(2, 60, clock=lambda: now[0])
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.retry_after("1.2.3.4") == 61
    assert limiter.retry_after("5.6.7.8") is None  # per address
    now[0] = 61.0
    assert limiter.retry_after("1.2.3.4") is None


def test_api_security_headers(client):
    r = client.get("/api/v1/health")
    assert r.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["Cache-Control"] == "no-store"
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers["X-Frame-Options"] == "DENY"
    docs = client.get("/docs")  # interactive docs need scripts: no API CSP there
    assert docs.status_code == 200 and "Content-Security-Policy" not in docs.headers


def test_active_sessions_list_and_revocation(client, auth_headers, db, settings):
    other_tab = {"Authorization": f"Bearer {login(client).json()['access_token']}"}
    listed = client.get("/api/v1/auth/sessions", headers=auth_headers).json()
    assert len(listed) == 2 and sum(s["current"] for s in listed) == 1

    other_id = next(s["id"] for s in listed if not s["current"])
    assert client.post(f"/api/v1/auth/sessions/{other_id}/revoke", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=other_tab).status_code == 401  # really revoked
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/auth/sessions/{other_id}/revoke", headers=auth_headers).status_code == 404

    third = {"Authorization": f"Bearer {login(client).json()['access_token']}"}
    msg = client.post("/api/v1/auth/sessions/revoke-others", headers=auth_headers).json()["message"]
    assert "1 other" in msg
    assert client.get("/api/v1/auth/me", headers=third).status_code == 401

    # Another administrator's sign-ins are invisible and cannot be revoked.
    create_admin(db, settings, "secondadmin", "Second-Admin-Pass-1", None)
    second = {"Authorization": f"Bearer {login(client, 'secondadmin', 'Second-Admin-Pass-1').json()['access_token']}"}
    second_id = client.get("/api/v1/auth/sessions", headers=second).json()[0]["id"]
    assert second_id not in [s["id"] for s in client.get("/api/v1/auth/sessions", headers=auth_headers).json()]
    assert client.post(f"/api/v1/auth/sessions/{second_id}/revoke", headers=auth_headers).status_code == 404

    current_id = next(s["id"] for s in client.get("/api/v1/auth/sessions", headers=auth_headers).json() if s["current"])
    assert client.post(f"/api/v1/auth/sessions/{current_id}/revoke", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401


def test_logs_never_contain_media_or_feature_values(client, auth_headers, caplog):
    caplog.set_level(logging.DEBUG)  # most verbose application logging
    caplog.set_level(logging.INFO, logger="sqlalchemy.engine")  # SQL logging switched on (worst case)
    sid = new_session(client, auth_headers)
    face = client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers).json()
    client.post(f"{SESSIONS}/{sid}/analysis/motion", json=pose_payload(), headers=auth_headers)
    voice = post_voice(client, auth_headers, sid).json()
    client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    client.get(f"{SESSIONS}/{sid}/report.pdf", headers=auth_headers)

    # SQLAlchemy adds timing notes such as "[cached since 0.2543s ago]" / "[generated in 0.0012s]";
    # their digits can match short feature values by chance, so drop them before searching.
    text = "\n".join(
        SQLALCHEMY_TIMING.sub("", r.getMessage()) if r.name.startswith("sqlalchemy") else r.getMessage()
        for r in caplog.records
    )
    assert "INSERT INTO voice_measurements" in text, "control: SQL statements must actually be logged"
    sensitive = [
        "RIFF", voice_wav()[44:60].hex(),  # raw audio
        str(voice["features"]["mfcc_mean"][1]), str(voice["features"]["f0_median_hz"]),  # voice features
        str(face["features"]["ear_mean"]), str(face["features"]["brightness_mean"]),  # face features
        "0.445",  # a landmark coordinate from the face fixture
        "f0_median_hz", "mfcc_mean",  # feature keys appear only inside JSON payloads
    ]
    leaked = [s for s in sensitive if s in text]
    assert leaked == [], f"sensitive values found in logs: {leaked}"
