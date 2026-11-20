"""Retention: find and delete analysis sessions whose retain_until date has passed.

Policy (consent text v1.0 + DATA_RETENTION_DAYS): a session is kept until its retain_until date;
afterwards it may be deleted. Sessions with retain_until = NULL are never purged.
Deleting a session removes its consent record, measurements and saved combined records through
the database's ON DELETE CASCADE foreign keys. Audit entries are kept (they hold no feature values).
"""

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import (
    AnalysisSession,
    CombinedResult,
    ConsentRecord,
    FacialMeasurement,
    MotionMeasurement,
    VoiceMeasurement,
)
from app.services import audit
from app.services.session_service import SessionError

TRIGGERS = ("manual", "automatic", "cli")


@dataclass
class ExpiredSession:
    id: int
    reference_code: str
    subject_label: str
    status: str
    retain_until: datetime
    consent_records: int
    face_measurements: int
    motion_measurements: int
    voice_measurements: int
    combined_records: int

    def as_dict(self) -> dict:
        return asdict(self)


def _count(model):
    return (
        select(func.count(model.id))
        .where(model.session_id == AnalysisSession.id)
        .correlate(AnalysisSession)
        .scalar_subquery()
    )


def find_expired(db: Session, now: datetime | None = None) -> list[ExpiredSession]:
    now = now or utcnow()
    rows = db.execute(
        select(
            AnalysisSession.id, AnalysisSession.reference_code, AnalysisSession.subject_label,
            AnalysisSession.status, AnalysisSession.retain_until,
            _count(ConsentRecord), _count(FacialMeasurement), _count(MotionMeasurement),
            _count(VoiceMeasurement), _count(CombinedResult),
        )
        .where(AnalysisSession.retain_until.is_not(None), AnalysisSession.retain_until < now)
        .order_by(AnalysisSession.retain_until, AnalysisSession.id)
    ).all()
    return [ExpiredSession(*row) for row in rows]


def purge(
    db: Session,
    *,
    trigger: str,
    admin_id: int | None = None,
    only_ids: set[int] | None = None,
    now: datetime | None = None,
    ip_address: str | None = None,
) -> list[ExpiredSession]:
    """Delete expired sessions (optionally only those in `only_ids`) in one transaction.

    The expiry condition is re-checked inside the DELETE; if the number of deleted rows differs
    from what was selected, everything is rolled back. Returns what was deleted.
    """
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown trigger {trigger!r}")
    now = now or utcnow()
    targets = find_expired(db, now)
    if only_ids is not None:
        targets = [t for t in targets if t.id in only_ids]
    if not targets:
        return []
    ids = [t.id for t in targets]
    try:
        result = db.execute(
            delete(AnalysisSession).where(
                AnalysisSession.id.in_(ids),
                AnalysisSession.retain_until.is_not(None),
                AnalysisSession.retain_until < now,
            )
        )
        if result.rowcount != len(ids):
            raise SessionError(409, "Sessions changed while purging; nothing was deleted. Preview again.")
        audit.record(
            db,
            "retention.purged",
            admin_id=admin_id,
            details={
                "trigger": trigger,
                "count": len(ids),
                "reference_codes": [t.reference_code for t in targets][:100],
            },
            ip_address=ip_address,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.expire_all()
    return targets
