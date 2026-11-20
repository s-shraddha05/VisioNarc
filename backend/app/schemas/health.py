from typing import Literal

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    full_name: str
    version: str
    environment: str
    server_time: UTCDateTime


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class DiagnosticsResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_version: str
    environment: str
    python_version: str
    database_dialect: str
    database_server_version: str | None
    database_reachable: bool
    migration_current: str | None
    migration_head: str | None
    migrations_up_to_date: bool
    admin_count: int | None
    store_raw_media: bool
    data_retention_days: int
    errors: list[str]
