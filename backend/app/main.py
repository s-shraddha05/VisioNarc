import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.routes import (
    analysis,
    audit_logs,
    auth,
    dashboard,
    health,
    retention,
    sessions,
    settings as settings_routes,
)
from app.core.config import APP_FULL_NAME, APP_NAME, APP_VERSION, Settings, get_settings
from app.db.errors import database_error_detail, mysql_error_code
from app.services.rate_limit import FailureRateLimiter
from app.services.retention_scheduler import RetentionScheduler

logger = logging.getLogger("visonarc")

# API responses are JSON/PDF only: forbid any active content and framing, never cache.
API_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def create_app(settings: Settings | None = None, session_factory: Callable[[], Session] | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_for_startup()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if settings.retention_auto_purge:
            if session_factory is not None:
                factory = session_factory
            else:
                from app.db.session import get_sessionmaker

                factory = get_sessionmaker()
            scheduler = RetentionScheduler(factory, settings.retention_purge_interval_hours)
            app.state.retention_scheduler = scheduler
            scheduler.start()
        yield
        if scheduler:
            await scheduler.stop()

    is_prod = settings.app_env == "production"
    app = FastAPI(
        title=APP_FULL_NAME,
        version=APP_VERSION,
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.login_limiter = FailureRateLimiter(settings.login_ip_max_failures, settings.login_ip_window_seconds)
    app.state.retention_scheduler = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition", "Retry-After"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(settings.api_prefix):
            for name, value in API_HEADERS.items():
                response.headers.setdefault(name, value)
        return response

    @app.exception_handler(OperationalError)
    async def database_unavailable(_request: Request, exc: OperationalError):
        code = mysql_error_code(exc)
        logger.error("Database operational error: %s (MySQL error %s)", exc.__class__.__name__, code or "n/a")
        return JSONResponse(status_code=503, content={"detail": database_error_detail(code)})

    api = APIRouter(prefix=settings.api_prefix)
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(dashboard.router)
    api.include_router(sessions.router)
    api.include_router(analysis.router)
    api.include_router(analysis.schema_router)
    api.include_router(audit_logs.router)
    api.include_router(retention.router)
    api.include_router(settings_routes.router)
    app.include_router(api)

    @app.get("/", include_in_schema=False)
    def root():
        return {"app": APP_NAME, "full_name": APP_FULL_NAME, "api": settings.api_prefix}

    return app


app = create_app()
