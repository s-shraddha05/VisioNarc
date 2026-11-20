import csv
import io
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.api.deps import AppSettings, CurrentAdmin, DbSession, client_ip
from app.core.config import APP_FULL_NAME
from app.schemas.common import Page
from app.schemas.sessions import SessionCreate, SessionDetail, SessionExport, SessionStatus, SessionSummary
from app.services import audit, report_service, session_service
from app.services.session_service import SessionError

router = APIRouter(prefix="/sessions", tags=["sessions"])

DISCLAIMER = (
    "Experimental academic behavioural-analysis record. Facial appearance, voice and movement "
    "cannot prove drug consumption; nothing in this record is a medical or forensic diagnosis."
)
CSV_EXPORT_LIMIT = 5000

StatusFilter = Annotated[list[SessionStatus] | None, Query(alias="status")]
SearchFilter = Annotated[str | None, Query(max_length=100)]


def _raise(exc: SessionError) -> None:
    raise HTTPException(exc.status_code, exc.detail) from None


@router.post("", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate, request: Request, db: DbSession, settings: AppSettings, admin: CurrentAdmin
):
    session = session_service.create_session(db, settings, admin, body, client_ip(request))
    return session_service.get_detail(db, session.id)


@router.get("", response_model=Page[SessionSummary])
def list_sessions(
    db: DbSession,
    _admin: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    statuses: StatusFilter = None,
    q: SearchFilter = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to.")
    items, total = session_service.list_sessions(
        db, page=page, page_size=page_size, statuses=statuses, q=q, date_from=date_from, date_to=date_to
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


def _csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    # Neutralise spreadsheet formula injection from free-text fields.
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@router.get("/export.csv")
def export_csv(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    statuses: StatusFilter = None,
    q: SearchFilter = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    rows = session_service.iter_sessions_for_export(
        db, limit=CSV_EXPORT_LIMIT, statuses=statuses, q=q, date_from=date_from, date_to=date_to
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([f"# {APP_FULL_NAME} - analysis session export. {DISCLAIMER}"])
    writer.writerow([
        "reference_code", "subject_label", "status", "created_at_utc", "completed_at_utc",
        "retain_until_utc", "created_by", "consent_face", "consent_motion", "consent_voice",
        "consent_withdrawn", "face_measurements", "motion_measurements", "voice_measurements",
        "combined_results",
    ])
    for s in rows:
        writer.writerow([_csv_cell(v) for v in (
            s.reference_code, s.subject_label, s.status, s.created_at.isoformat(),
            s.completed_at.isoformat() if s.completed_at else "",
            s.retain_until.isoformat() if s.retain_until else "", s.created_by,
            s.allow_face, s.allow_motion, s.allow_voice, s.consent_withdrawn,
            s.counts.face, s.counts.motion, s.counts.voice, s.counts.results,
        )])
    audit.record(
        db, "session.exported_csv", admin_id=admin.id, details={"rows": len(rows)},
        ip_address=client_ip(request),
    )
    db.commit()
    filename = f"visonarc-sessions-{datetime.now(UTC):%Y%m%d-%H%M%S}.csv"
    return Response(
        content="﻿" + buffer.getvalue(),  # BOM so Excel opens UTF-8 correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: DbSession, _admin: CurrentAdmin):
    try:
        return session_service.get_detail(db, session_id)
    except SessionError as exc:
        _raise(exc)


@router.get("/{session_id}/export", response_model=SessionExport)
def export_session(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        detail = session_service.get_detail(db, session_id)
    except SessionError as exc:
        _raise(exc)
    audit.record(
        db, "session.exported_json", admin_id=admin.id, entity_type="analysis_session",
        entity_id=session_id, ip_address=client_ip(request),
    )
    db.commit()
    return SessionExport(
        app=APP_FULL_NAME,
        generated_at=datetime.now(UTC),
        generated_by=admin.username,
        disclaimer=DISCLAIMER,
        session=detail,
    )


@router.get("/{session_id}/report.pdf", response_class=Response)
def session_report_pdf(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    """Server-generated PDF of the session record (single admin role: any signed-in admin)."""
    try:
        detail = session_service.get_detail(db, session_id)
    except SessionError as exc:
        _raise(exc)
    pdf = report_service.build_session_report(detail, generated_by=admin.username)
    audit.record(
        db, "session.report_pdf", admin_id=admin.id, entity_type="analysis_session", entity_id=session_id,
        details={"reference_code": detail.reference_code, "bytes": len(pdf)}, ip_address=client_ip(request),
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="visonarc-{detail.reference_code}.pdf"'},
    )


@router.post("/{session_id}/withdraw-consent", response_model=SessionDetail)
def withdraw_consent(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        session_service.withdraw_consent(db, admin, session_id, client_ip(request))
        return session_service.get_detail(db, session_id)
    except SessionError as exc:
        _raise(exc)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        session_service.delete_session(db, admin, session_id, client_ip(request))
    except SessionError as exc:
        _raise(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
