import secrets
from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.db.base import utcnow
from app.models import (
    Admin,
    AnalysisSession,
    CombinedResult,
    ConsentRecord,
    FacialMeasurement,
    MotionMeasurement,
    ScreeningResult,
    VoiceMeasurement,
)
from app.schemas.sessions import (
    CONSENT_TEXT_VERSION,
    MeasurementCounts,
    SessionCreate,
    SessionDetail,
    SessionSummary,
)
from app.services import audit

# Statuses that still accept new captures.
ACTIVE_STATUSES = ("consented", "in_progress")


class SessionError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _new_reference_code(db: Session) -> str:
    for _ in range(10):
        code = f"VN-{utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}"
        if db.scalar(select(AnalysisSession.id).where(AnalysisSession.reference_code == code)) is None:
            return code
    raise SessionError(500, "Could not allocate a unique reference code; please retry.")


def create_session(
    db: Session, settings: Settings, admin: Admin, body: SessionCreate, ip_address: str | None
) -> AnalysisSession:
    now = utcnow()
    consent = body.consent
    session = AnalysisSession(
        reference_code=_new_reference_code(db),
        subject_label=body.subject_label,
        notes=body.notes,
        status="consented",
        created_by_admin_id=admin.id,
        retain_until=now + timedelta(days=settings.data_retention_days),
        consent=ConsentRecord(
            consent_given=True,
            consent_text_version=CONSENT_TEXT_VERSION,
            consented_by_label=consent.consented_by_label,
            allow_face=consent.allow_face,
            allow_motion=consent.allow_motion,
            allow_voice=consent.allow_voice,
            # Raw media is kept only if the server allows it AND the subject agreed.
            allow_raw_media_storage=consent.allow_raw_media_storage and settings.store_raw_media,
            recorded_by_admin_id=admin.id,
            consented_at=now,
        ),
    )
    db.add(session)
    db.flush()
    audit.record(
        db,
        "session.created",
        admin_id=admin.id,
        entity_type="analysis_session",
        entity_id=session.id,
        details={
            "reference_code": session.reference_code,
            "modalities": [
                m for m, ok in (("face", consent.allow_face), ("motion", consent.allow_motion),
                                ("voice", consent.allow_voice)) if ok
            ],
        },
        ip_address=ip_address,
    )
    db.commit()
    return session


def _count(model) -> Select:
    return (
        select(func.count(model.id))
        .where(model.session_id == AnalysisSession.id)
        .correlate(AnalysisSession)
        .scalar_subquery()
    )


def _summary_query() -> Select:
    return (
        select(
            AnalysisSession,
            Admin.username,
            _count(FacialMeasurement).label("face"),
            _count(MotionMeasurement).label("motion"),
            _count(VoiceMeasurement).label("voice"),
            _count(CombinedResult).label("results"),
        )
        .outerjoin(Admin, Admin.id == AnalysisSession.created_by_admin_id)
        .options(selectinload(AnalysisSession.consent))
    )


def _to_summary(row) -> SessionSummary:
    s: AnalysisSession = row[0]
    c = s.consent
    return SessionSummary(
        id=s.id,
        reference_code=s.reference_code,
        subject_label=s.subject_label,
        status=s.status,
        created_at=s.created_at,
        updated_at=s.updated_at,
        completed_at=s.completed_at,
        retain_until=s.retain_until,
        created_by=row.username,
        allow_face=bool(c and c.allow_face),
        allow_motion=bool(c and c.allow_motion),
        allow_voice=bool(c and c.allow_voice),
        consent_withdrawn=bool(c and c.withdrawn_at),
        counts=MeasurementCounts(face=row.face, motion=row.motion, voice=row.voice, results=row.results),
        is_synthetic=s.is_synthetic,
    )


def _apply_filters(
    stmt: Select,
    statuses: list[str] | None,
    q: str | None,
    date_from: date | None,
    date_to: date | None,
) -> Select:
    if statuses:
        stmt = stmt.where(AnalysisSession.status.in_(statuses))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(AnalysisSession.reference_code.ilike(pattern), AnalysisSession.subject_label.ilike(pattern))
        )
    if date_from:
        stmt = stmt.where(AnalysisSession.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(AnalysisSession.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return stmt


def list_sessions(
    db: Session,
    *,
    page: int,
    page_size: int,
    statuses: list[str] | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[SessionSummary], int]:
    base = _apply_filters(select(AnalysisSession.id), statuses, q, date_from, date_to)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = _apply_filters(_summary_query(), statuses, q, date_from, date_to)
    stmt = stmt.order_by(AnalysisSession.created_at.desc(), AnalysisSession.id.desc())
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return [_to_summary(r) for r in rows], total


def iter_sessions_for_export(db: Session, *, limit: int, **filters) -> list[SessionSummary]:
    stmt = _apply_filters(_summary_query(), **filters)
    stmt = stmt.order_by(AnalysisSession.created_at.desc(), AnalysisSession.id.desc()).limit(limit)
    return [_to_summary(r) for r in db.execute(stmt).all()]


def _get(db: Session, session_id: int) -> AnalysisSession:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    return session


def get_detail(db: Session, session_id: int) -> SessionDetail:
    row = db.execute(_summary_query().where(AnalysisSession.id == session_id)).first()
    if row is None:
        raise SessionError(404, "Analysis session not found.")
    s: AnalysisSession = row[0]
    summary = _to_summary(row)
    return SessionDetail(
        **summary.model_dump(),
        notes=s.notes,
        consent=s.consent,
        facial_measurements=sorted(s.facial_measurements, key=lambda m: m.captured_at),
        motion_measurements=sorted(s.motion_measurements, key=lambda m: m.captured_at),
        voice_measurements=sorted(s.voice_measurements, key=lambda m: m.captured_at),
        combined_results=sorted(s.combined_results, key=lambda r: r.created_at),
        screening_results=sorted(s.screening_results, key=lambda r: (r.created_at, r.id)),
    )


def withdraw_consent(db: Session, admin: Admin, session_id: int, ip_address: str | None) -> None:
    """Withdrawal cancels the session and deletes every derived measurement and result.

    The session and consent rows remain (with withdrawn_at) as evidence that consent was withdrawn.
    """
    session = _get(db, session_id)
    if session.consent is None or session.consent.withdrawn_at is not None:
        raise SessionError(409, "Consent has already been withdrawn for this session.")
    removed = {}
    for key, model in (
        ("face", FacialMeasurement),
        ("motion", MotionMeasurement),
        ("voice", VoiceMeasurement),
        ("screening", ScreeningResult),
        ("results", CombinedResult),
    ):
        removed[key] = db.execute(delete(model).where(model.session_id == session.id)).rowcount
    session.consent.withdrawn_at = utcnow()
    session.status = "cancelled"
    audit.record(
        db,
        "session.consent_withdrawn",
        admin_id=admin.id,
        entity_type="analysis_session",
        entity_id=session.id,
        details={"reference_code": session.reference_code, "deleted": removed},
        ip_address=ip_address,
    )
    db.commit()
    db.expire_all()


def delete_session(db: Session, admin: Admin, session_id: int, ip_address: str | None) -> str:
    session = _get(db, session_id)
    reference = session.reference_code
    db.delete(session)
    audit.record(
        db,
        "session.deleted",
        admin_id=admin.id,
        entity_type="analysis_session",
        entity_id=session_id,
        details={"reference_code": reference},
        ip_address=ip_address,
    )
    db.commit()
    return reference
