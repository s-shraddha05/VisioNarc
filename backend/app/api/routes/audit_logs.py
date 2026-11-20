from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdmin, DbSession
from app.models import Admin, AuditLog
from app.schemas.common import Page
from app.schemas.dashboard import AuditEventOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def _base() -> Select:
    return select(AuditLog, Admin.username).outerjoin(Admin, Admin.id == AuditLog.admin_id)


def _to_out(row) -> AuditEventOut:
    log: AuditLog = row[0]
    return AuditEventOut(
        id=log.id,
        action=log.action,
        admin_username=row.username,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        details=log.details,
        ip_address=log.ip_address,
        created_at=log.created_at,
    )


def recent_events(db: Session, limit: int) -> list[AuditEventOut]:
    stmt = _base().order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    return [_to_out(r) for r in db.execute(stmt).all()]


@router.get("", response_model=Page[AuditEventOut])
def list_audit_logs(
    db: DbSession,
    _admin: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    action: Annotated[str | None, Query(max_length=64)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to.")
    filters = []
    if action:
        # "auth" matches every auth.* action; "auth.login" matches exactly.
        filters.append(
            AuditLog.action == action if "." in action else AuditLog.action.like(f"{action}.%")
        )
    if date_from:
        filters.append(AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        filters.append(AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    total = db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0
    stmt = (
        _base()
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page(items=[_to_out(r) for r in db.execute(stmt).all()], total=total, page=page, page_size=page_size)


@router.get("/actions", response_model=list[str])
def list_actions(db: DbSession, _admin: CurrentAdmin):
    return list(db.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action)))
