from datetime import date
from typing import Any

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class DayCount(BaseModel):
    date: date
    count: int


class DashboardTotals(BaseModel):
    sessions: int
    active_sessions: int
    completed_sessions: int
    face_measurements: int
    motion_measurements: int
    voice_measurements: int
    combined_results: int


class AuditEventOut(BaseModel):
    id: int
    action: str
    admin_username: str | None
    entity_type: str | None
    entity_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: UTCDateTime


class DashboardSummary(BaseModel):
    generated_at: UTCDateTime
    totals: DashboardTotals
    sessions_by_status: dict[str, int]
    sessions_per_day: list[DayCount]
    recent_activity: list[AuditEventOut]
