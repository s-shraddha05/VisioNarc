from alembic import command
from alembic.config import Config
from sqlalchemy.exc import OperationalError

from app.core.config import APP_FULL_NAME, BACKEND_DIR
from app.db.session import get_db


def test_health_is_public_and_branded(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["full_name"] == APP_FULL_NAME


def test_readiness_ok(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class _BrokenSession:
    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def scalar(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_readiness_reports_database_outage(client):
    client.app.dependency_overrides[get_db] = lambda: _BrokenSession()
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_database_outage_on_protected_route_returns_503(client):
    client.app.dependency_overrides[get_db] = lambda: _BrokenSession()
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer x.y.z"})
    # Token is rejected before the DB is queried, so this is still a clean 401...
    assert response.status_code == 401
    # ...while a login, which must hit the DB, reports the outage instead of a 500.
    response = client.post("/api/v1/auth/login", json={"username": "a", "password": "b"})
    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]


def test_diagnostics_requires_auth(client):
    assert client.get("/api/v1/health/details").status_code == 401


def test_diagnostics_flags_missing_migrations(client, auth_headers):
    # Test DB was built with create_all, so there is no alembic_version table.
    body = client.get("/api/v1/health/details", headers=auth_headers).json()
    assert body["database_reachable"] is True
    assert body["database_dialect"] == "sqlite"
    assert body["admin_count"] == 1
    assert body["migration_head"] == "0003"
    assert body["migrations_up_to_date"] is False
    assert body["status"] == "degraded"


def test_diagnostics_ok_after_migrations(client, auth_headers, engine):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.stamp(config, "head")
    body = client.get("/api/v1/health/details", headers=auth_headers).json()
    assert body["migrations_up_to_date"] is True
    assert body["status"] == "ok", body["errors"]
