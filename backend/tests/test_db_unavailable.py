"""Route behaviour when the database cannot be reached (a real connection failure, not a mock).

Documented in docs/ARCHITECTURE.md ("Behaviour when the database is unavailable").
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app

DB_DOWN = {"detail": "Database unavailable. Check that MySQL is running."}


@pytest.fixture
def down_client(settings, tmp_path):
    # SQLite cannot open a file in a directory that does not exist -> OperationalError on connect.
    engine = create_engine(f"sqlite:///{tmp_path / 'missing-dir' / 'db.sqlite'}")
    factory = sessionmaker(bind=engine)
    app = create_app(settings)

    def _get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    engine.dispose()


def test_liveness_works_without_database(down_client):
    assert down_client.get("/api/v1/health").status_code == 200


def test_readiness_reports_outage(down_client):
    r = down_client.get("/api/v1/health/ready")
    assert r.status_code == 503 and r.json() == {"status": "degraded", "database": "unavailable"}


def test_login_reports_outage_not_wrong_password(down_client):
    r = down_client.post("/api/v1/auth/login", json={"username": "a", "password": "b"})
    assert r.status_code == 503 and r.json() == DB_DOWN


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/v1/auth/me"),
        ("get", "/api/v1/sessions"),
        ("get", "/api/v1/dashboard/summary"),
        ("get", "/api/v1/settings"),
        ("get", "/api/v1/analysis/feature-schema"),
        ("get", "/api/v1/retention/preview"),
        ("get", "/api/v1/sessions/1/report.pdf"),
    ],
)
def test_authenticated_routes_return_503_with_a_valid_token(down_client, settings, method, path):
    # Signature-valid token: it passes decoding, then the session lookup needs the database.
    token, _, _ = create_access_token(1, settings)
    r = getattr(down_client, method)(path, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 503 and r.json() == DB_DOWN


def test_invalid_tokens_are_rejected_without_the_database(down_client):
    assert down_client.get("/api/v1/sessions").status_code == 401
    assert down_client.get("/api/v1/sessions", headers={"Authorization": "Bearer garbage"}).status_code == 401


class _DriverError(Exception):
    """Stand-in for a PyMySQL error: args[0] is the MySQL error code."""


@pytest.mark.parametrize(
    "code, expected",
    [
        (2003, "Database unavailable. Check that MySQL is running."),
        (2013, "Database unavailable. Check that MySQL is running."),
        (1045, "DB_USER and DB_PASSWORD"),
        (1044, "has no access to the configured database"),
        (1049, "does not exist"),
        (None, "Database unavailable. Check that MySQL is running."),
    ],
)
def test_mysql_error_codes_map_to_specific_messages(settings, code, expected):
    from sqlalchemy.exc import OperationalError

    password = "secret-password-value"
    orig = _DriverError(code, f"Access denied for user 'visonarc_app' (using password: {password})") if code else _DriverError("x")

    def _broken_db():
        raise OperationalError("SELECT 1", {}, orig)
        yield  # pragma: no cover

    app = create_app(settings)
    app.dependency_overrides[get_db] = _broken_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "a", "password": "b"})
    assert r.status_code == 503
    assert expected in r.json()["detail"]
    # The driver's own text (user names, password hints) never reaches the client.
    assert "visonarc_app" not in r.text and password not in r.text
