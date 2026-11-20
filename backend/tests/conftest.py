"""Unit/API tests run against an in-memory SQLite database built from the models.

The real MySQL database is only touched by tests marked `mysql` (opt-in).
"""

import os

# Must be set before app modules are imported (app.main builds the app at import time).
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-0123456789"
os.environ["APP_ENV"] = "test"
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.services.auth_service import create_admin

TEST_ADMIN_USERNAME = "testadmin"
TEST_ADMIN_PASSWORD = "Test-Password-2026"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite://",
        jwt_secret_key=os.environ["JWT_SECRET_KEY"],
        bcrypt_rounds=4,
        login_max_failed_attempts=3,
        login_lockout_minutes=15,
    )


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        hide_parameters=True,  # same as production (app/db/session.py)
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def admin(db, settings):
    return create_admin(db, settings, TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD, "Test Admin")


@pytest.fixture
def client(settings, session_factory):
    app = create_app(settings)

    def _get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


def login(client, username=TEST_ADMIN_USERNAME, password=TEST_ADMIN_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


@pytest.fixture
def auth_headers(client, admin):
    response = login(client)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
