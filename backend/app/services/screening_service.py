"""Experimental screening: who may run it, and how results are stored.

There is no validated model. With SCREENING_MODE=synthetic_demo the hand-set demo formula
(app/analysis/screening.py) runs on sessions flagged is_synthetic only; real sessions always get
"unavailable" and nothing is computed or stored for them. Results are saved once and the website
and PDF both read the saved row.
"""

from sqlalchemy.orm import Session

from app.analysis import screening
from app.core.config import Settings
from app.models import Admin, AnalysisSession, ScreeningResult
from app.schemas.screening import ScreeningOverview
from app.services import analysis_service, audit
from app.services.session_service import SessionError

UNAVAILABLE_REAL = (
    "No validated model exists, so no estimate or classification is produced for real sessions. "
    "No reliable estimate is available."
)
DISABLED = "Experimental screening is turned off (SCREENING_MODE=off)."
DEMO_READY = (
    "Synthetic demonstration session. The demo formula uses hand-set weights; its score is not a "
    "probability about any real person."
)


def _session(db: Session, session_id: int) -> AnalysisSession:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    return session


def _results(session: AnalysisSession) -> list[ScreeningResult]:
    return sorted(session.screening_results, key=lambda r: (r.created_at, r.id), reverse=True)


def overview(db: Session, session_id: int, settings: Settings) -> ScreeningOverview:
    session = _session(db, session_id)
    if not session.is_synthetic:
        status, message, can_run = "unavailable", UNAVAILABLE_REAL, False
    elif settings.screening_mode != "synthetic_demo":
        status, message, can_run = "unavailable", DISABLED, False
    else:
        status, message, can_run = "synthetic_demo", DEMO_READY, True
    return ScreeningOverview(
        mode=settings.screening_mode, session_is_synthetic=session.is_synthetic, can_run=can_run,
        model_status=status, message=message, results=_results(session),
    )


def run(db: Session, admin: Admin, session_id: int, settings: Settings, ip: str | None) -> ScreeningResult:
    session = _session(db, session_id)
    if not session.is_synthetic:
        raise SessionError(409, UNAVAILABLE_REAL)
    if settings.screening_mode != "synthetic_demo":
        raise SessionError(409, DISABLED)
    if session.consent is None or session.consent.withdrawn_at is not None:
        raise SessionError(409, "Consent is missing or was withdrawn; screening cannot run.")
    records = analysis_service.list_integrations(db, session_id)
    if not records:
        raise SessionError(409, "Save a combined record first; screening uses the latest saved record.")
    record = records[0]
    modality_status = record.explanation.get("modality_status", {})
    outcome = screening.score(record.features or [], record.feature_schema_version, modality_status)

    result = ScreeningResult(
        session_id=session.id,
        combined_result_id=record.id,
        created_by_admin_id=admin.id,
        model_name=screening.MODEL_NAME,
        model_version=screening.MODEL_VERSION,
        model_status=outcome.model_status,
        is_synthetic=True,
        target_definition=screening.TARGET_DEFINITION,
        feature_schema_version=record.feature_schema_version,
        input_measurement_ids={s["modality"]: s["measurement_id"] for s in record.source_measurements or []},
        modality_status=modality_status,
        missing_modalities=outcome.missing_modalities,
        coverage=outcome.coverage,
        estimate=outcome.estimate,
        classification=outcome.classification,
        decision_threshold=screening.DECISION_THRESHOLD if outcome.estimate is not None else None,
        explanation={
            "method": "Hand-set demonstration formula: sigmoid of a weighted sum of standardised features. "
            "Not trained, not validated.",
            "reasons": outcome.reasons,
            "contributions": outcome.contributions,
        },
        limitations=screening.LIMITATIONS,
    )
    db.add(result)
    db.flush()
    audit.record(
        db, "screening.synthetic_recorded", admin_id=admin.id, entity_type="analysis_session",
        entity_id=session.id, details={"result_id": result.id, "model_status": result.model_status},
        ip_address=ip,
    )
    db.commit()
    db.refresh(result)
    return result
