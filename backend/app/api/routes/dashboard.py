from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentAdmin, DbSession
from app.api.routes.audit_logs import recent_events
from app.db.base import utcnow
from app.models import (
    AnalysisSession,
    CombinedResult,
    FacialMeasurement,
    MotionMeasurement,
    VoiceMeasurement,
)
from app.schemas.dashboard import DashboardSummary, DashboardTotals, DayCount
from app.services.session_service import ACTIVE_STATUSES

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: DbSession, _admin: CurrentAdmin, days: Annotated[int, Query(ge=7, le=90)] = 14):
    """Every number here is counted from persisted rows; nothing is estimated or sampled."""
    by_status = dict(
        db.execute(select(AnalysisSession.status, func.count()).group_by(AnalysisSession.status)).all()
    )

    def count(model) -> int:
        return db.scalar(select(func.count(model.id))) or 0

    today = utcnow().date()
    start = today - timedelta(days=days - 1)
    created = db.scalars(
        select(AnalysisSession.created_at).where(
            AnalysisSession.created_at >= datetime.combine(start, datetime.min.time())
        )
    ).all()
    per_day = {start + timedelta(days=i): 0 for i in range(days)}
    for ts in created:
        if ts.date() in per_day:
            per_day[ts.date()] += 1

    return DashboardSummary(
        generated_at=datetime.now(UTC),
        totals=DashboardTotals(
            sessions=sum(by_status.values()),
            active_sessions=sum(by_status.get(s, 0) for s in ACTIVE_STATUSES),
            completed_sessions=by_status.get("completed", 0),
            face_measurements=count(FacialMeasurement),
            motion_measurements=count(MotionMeasurement),
            voice_measurements=count(VoiceMeasurement),
            combined_results=count(CombinedResult),
        ),
        sessions_by_status=by_status,
        sessions_per_day=[DayCount(date=d, count=c) for d, c in per_day.items()],
        recent_activity=recent_events(db, limit=8),
    )
