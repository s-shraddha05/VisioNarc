from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, CurrentAdmin, DbSession, client_ip
from app.db.base import utcnow
from app.schemas.common import UTCDateTime
from app.services import retention_service
from app.services.session_service import SessionError

router = APIRouter(prefix="/retention", tags=["retention"])


class ExpiredSessionOut(BaseModel):
    id: int
    reference_code: str
    subject_label: str
    status: str
    retain_until: UTCDateTime
    consent_records: int
    face_measurements: int
    motion_measurements: int
    voice_measurements: int
    combined_records: int


class RetentionPreview(BaseModel):
    checked_at: UTCDateTime
    retention_days: int
    auto_purge_enabled: bool
    interval_hours: int
    last_automatic_run: dict | None
    sessions: list[ExpiredSessionOut]


class PurgeRequest(BaseModel):
    # The ids shown in the preview; only those still expired are deleted.
    session_ids: list[int] = Field(min_length=1, max_length=1000)
    confirm: Literal[True]


class PurgeResult(BaseModel):
    deleted: list[ExpiredSessionOut]
    skipped_ids: list[int]


@router.get("/preview", response_model=RetentionPreview)
def preview(request: Request, db: DbSession, settings: AppSettings, _admin: CurrentAdmin):
    scheduler = getattr(request.app.state, "retention_scheduler", None)
    return RetentionPreview(
        checked_at=utcnow(),
        retention_days=settings.data_retention_days,
        auto_purge_enabled=settings.retention_auto_purge,
        interval_hours=settings.retention_purge_interval_hours,
        last_automatic_run=scheduler.last_run if scheduler else None,
        sessions=[ExpiredSessionOut(**s.as_dict()) for s in retention_service.find_expired(db)],
    )


@router.post("/purge", response_model=PurgeResult)
def purge(body: PurgeRequest, request: Request, db: DbSession, admin: CurrentAdmin):
    wanted = set(body.session_ids)
    try:
        deleted = retention_service.purge(
            db, trigger="manual", admin_id=admin.id, only_ids=wanted, ip_address=client_ip(request)
        )
    except SessionError as exc:
        raise HTTPException(exc.status_code, exc.detail) from None
    deleted_ids = {d.id for d in deleted}
    return PurgeResult(
        deleted=[ExpiredSessionOut(**d.as_dict()) for d in deleted],
        skipped_ids=sorted(wanted - deleted_ids),
    )
