import platform
from datetime import UTC, datetime

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AppSettings, CurrentAdmin, DbSession
from app.core.config import APP_FULL_NAME, APP_NAME, APP_VERSION, BACKEND_DIR
from app.models import Admin
from app.schemas.health import DiagnosticsResponse, HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


def migration_head() -> str | None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("", response_model=HealthResponse)
def health(settings: AppSettings):
    """Liveness: the API process is up. Does not touch the database."""
    return HealthResponse(
        status="ok",
        app=APP_NAME,
        full_name=APP_FULL_NAME,
        version=APP_VERSION,
        environment=settings.app_env,
        server_time=datetime.now(UTC),
    )


@router.get("/ready", response_model=ReadinessResponse)
def readiness(db: DbSession, response: Response):
    """Readiness: the database answers. Public, so it reports no details."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", database="unavailable")
    return ReadinessResponse(status="ok", database="ok")


@router.get("/details", response_model=DiagnosticsResponse)
def diagnostics(db: DbSession, settings: AppSettings, _admin: CurrentAdmin):
    errors: list[str] = []
    dialect = db.get_bind().dialect.name
    server_version = current = None
    reachable = False
    admin_count = None
    try:
        version_sql = "SELECT sqlite_version()" if dialect == "sqlite" else "SELECT VERSION()"
        server_version = db.execute(text(version_sql)).scalar_one()
        reachable = True
        admin_count = db.scalar(select(func.count(Admin.id)))
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError as exc:
        db.rollback()
        errors.append(f"Database check failed: {exc.__class__.__name__}")

    try:
        head = migration_head()
    except Exception as exc:  # noqa: BLE001 - diagnostics must report, not crash
        head = None
        errors.append(f"Could not read migrations: {exc.__class__.__name__}")

    up_to_date = current is not None and current == head
    if reachable and not up_to_date:
        errors.append("Database schema is not at the latest migration. Run: alembic upgrade head")

    return DiagnosticsResponse(
        status="ok" if reachable and up_to_date and not errors else "degraded",
        app_version=APP_VERSION,
        environment=settings.app_env,
        python_version=platform.python_version(),
        database_dialect=dialect,
        database_server_version=server_version,
        database_reachable=reachable,
        migration_current=current,
        migration_head=head,
        migrations_up_to_date=up_to_date,
        admin_count=admin_count,
        store_raw_media=settings.store_raw_media,
        data_retention_days=settings.data_retention_days,
        errors=errors,
    )
