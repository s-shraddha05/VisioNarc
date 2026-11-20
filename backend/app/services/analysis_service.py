"""Consent-gated persistence of measurements and the multimodal summary.

Audit entries record *that* a measurement was made (id, modality, reliability) but never the
feature values or any audio/landmark data.
"""

from datetime import UTC, datetime

import numpy as np
from sqlalchemy.orm import Session

from app.analysis import face as face_extractor
from app.analysis import motion as motion_extractor
from app.analysis import voice as voice_extractor
from app.analysis.common import ExtractionResult
from app.analysis.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    FEATURES,
    INTEGRATION_FEATURES,
    INTEGRATION_VERSION,
    LIMITATIONS,
    MIXED_SCHEMAS,
    MODALITY_ORDER,
    PROVENANCE_LABELS,
    SOURCES,
    spec,
)
from app.db.base import utcnow
from app.models import (
    Admin,
    AnalysisSession,
    CombinedResult,
    FacialMeasurement,
    MotionMeasurement,
    VoiceMeasurement,
)
from app.schemas.analysis import FaceSubmission, FeatureValue, ModalitySummary, MotionSubmission, MultimodalSummary
from app.services import audit
from app.services.session_service import ACTIVE_STATUSES, SessionError

CONSENT_FIELD = {"face": "allow_face", "motion": "allow_motion", "voice": "allow_voice"}


def session_for_capture(db: Session, session_id: int, modality: str) -> AnalysisSession:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    consent = session.consent
    if consent is None or not consent.consent_given:
        raise SessionError(403, "No consent is recorded for this session.")
    if consent.withdrawn_at is not None:
        raise SessionError(409, "Consent was withdrawn for this session; no further analysis is allowed.")
    if not getattr(consent, CONSENT_FIELD[modality]):
        raise SessionError(403, f"The recorded consent does not cover {modality} analysis.")
    if session.status not in ACTIVE_STATUSES:
        raise SessionError(409, f"This session is {session.status.replace('_', ' ')} and no longer accepts captures.")
    return session


def _finish(db: Session, session: AnalysisSession, admin: Admin, modality: str, measurement, ip: str | None):
    db.add(measurement)
    if session.status == "consented":
        session.status = "in_progress"
    db.flush()
    audit.record(
        db,
        f"analysis.{modality}_measured",
        admin_id=admin.id,
        entity_type="analysis_session",
        entity_id=session.id,
        details={"measurement_id": measurement.id, "is_reliable": measurement.is_reliable},
        ip_address=ip,
    )
    db.commit()
    db.refresh(measurement)
    return measurement


def _common(result: ExtractionResult, source: str, extractor_version: str) -> dict:
    return {
        "source": source,
        "extractor_version": extractor_version,
        "quality_score": result.quality_score,
        "is_reliable": result.is_reliable,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": result.features,
        "warnings": result.warnings,
    }


def record_face(db, admin, session, body: FaceSubmission, result: ExtractionResult, ip):
    m = FacialMeasurement(
        session_id=session.id,
        image_width=body.image_width,
        image_height=body.image_height,
        face_detected=True,
        brightness=body.pixel_stats.brightness_mean,
        sharpness=body.pixel_stats.sharpness_laplacian_var,
        **_common(result, body.source, face_extractor.EXTRACTOR_VERSION),
    )
    return _finish(db, session, admin, "face", m, ip)


def record_motion(db, admin, session, body: MotionSubmission, result: ExtractionResult, ip):
    m = MotionMeasurement(
        session_id=session.id,
        duration_seconds=result.features["duration_s"],
        frames_processed=len(body.frames),
        frames_with_pose=round(result.features["tracked_fraction"] * len(body.frames)),
        **_common(result, body.source, motion_extractor.EXTRACTOR_VERSION),
    )
    return _finish(db, session, admin, "motion", m, ip)


def record_voice(db, admin, session, source: str, result: ExtractionResult, sample_rate: int, ip):
    m = VoiceMeasurement(
        session_id=session.id,
        duration_seconds=result.features["duration_s"],
        sample_rate=sample_rate,
        snr_db=result.features["snr_db_estimate"],
        **_common(result, source, voice_extractor.EXTRACTOR_VERSION),
    )
    return _finish(db, session, admin, "voice", m, ip)


def motion_arrays(body: MotionSubmission) -> tuple[np.ndarray, np.ndarray]:
    times = np.array([f.t_ms for f in body.frames], dtype=float)
    lms = np.full((len(body.frames), 33, 4), np.nan)
    for i, f in enumerate(body.frames):
        if f.landmarks is not None:
            lms[i] = f.landmarks
    return times, lms


def _summarise(modality: str, consented: bool, withdrawn: bool, items: list) -> ModalitySummary:
    base = dict(modality=modality, measurement_count=len(items), measurement_id=None, captured_at=None,
                source=None, quality_score=None, is_reliable=None, warnings=[], key_features=[])
    if withdrawn:
        return ModalitySummary(status="consent_withdrawn", status_reason="Consent was withdrawn; data was deleted.", **base)
    if not consented:
        return ModalitySummary(status="not_consented", status_reason="Not covered by the recorded consent; excluded.", **base)
    if not items:
        return ModalitySummary(status="missing", status_reason="No measurement captured yet; excluded.", **base)
    reliable = [m for m in items if m.is_reliable]
    chosen = max(reliable or items, key=lambda m: (m.captured_at, m.id))
    features = [
        FeatureValue(
            key=spec.key, label=spec.label, unit=spec.unit, value=chosen.features.get(spec.key),
            provenance=spec.provenance, provenance_label=PROVENANCE_LABELS[spec.provenance],
        )
        for spec in FEATURES
        if spec.modality == modality and spec.summary
    ]
    status = "available" if reliable else "low_quality"
    reason = (
        "Latest measurement that passed all quality checks."
        if reliable
        else "Only measurements that failed one or more quality checks exist; interpret with extra caution."
    )
    base.update(measurement_id=chosen.id, captured_at=chosen.captured_at, source=chosen.source,
                quality_score=chosen.quality_score, is_reliable=chosen.is_reliable, warnings=chosen.warnings,
                key_features=features)
    return ModalitySummary(status=status, status_reason=reason, **base)


def multimodal_summary(db: Session, session_id: int) -> MultimodalSummary:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    consent = session.consent
    withdrawn = bool(consent and consent.withdrawn_at)
    modalities = [
        _summarise("face", bool(consent and consent.allow_face), withdrawn, session.facial_measurements),
        _summarise("motion", bool(consent and consent.allow_motion), withdrawn, session.motion_measurements),
        _summarise("voice", bool(consent and consent.allow_voice), withdrawn, session.voice_measurements),
    ]
    used = {spec.source for spec in FEATURES if spec.source}
    return MultimodalSummary(
        session_id=session.id,
        reference_code=session.reference_code,
        session_status=session.status,
        generated_at=datetime.now(UTC),
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        available_modalities=[m.modality for m in modalities if m.status in ("available", "low_quality")],
        missing_modalities=[m.modality for m in modalities if m.status not in ("available", "low_quality")],
        modalities=modalities,
        limitations=LIMITATIONS,
        method_sources={k: v for k, v in SOURCES.items() if k in used},
    )


def complete_session(db: Session, admin: Admin, session_id: int, ip: str | None) -> None:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    if session.status not in ACTIVE_STATUSES or (session.consent and session.consent.withdrawn_at):
        raise SessionError(409, f"A {session.status.replace('_', ' ')} session cannot be completed.")
    if not (session.facial_measurements or session.motion_measurements or session.voice_measurements):
        raise SessionError(409, "Capture at least one measurement before completing the session.")
    session.status = "completed"
    session.completed_at = utcnow()
    audit.record(db, "session.completed", admin_id=admin.id, entity_type="analysis_session", entity_id=session.id,
                 details={"reference_code": session.reference_code}, ip_address=ip)
    db.commit()


# ---- Feature integration (persisted, score-free) ------------------------------------------------

INTEGRATION_STATUSES = ("consented", "in_progress", "completed")


def _measurements(session: AnalysisSession, modality: str) -> list:
    items = {
        "face": session.facial_measurements,
        "motion": session.motion_measurements,
        "voice": session.voice_measurements,
    }[modality]
    # Defensive isolation check: only this session's rows can ever be integrated.
    return [m for m in items if m.session_id == session.id]


def create_integration(db: Session, admin: Admin, session_id: int, ip: str | None) -> CombinedResult:
    """Persist an ordered, provenance-tagged record of the session's reliable measurements.

    Produces no score, probability, confidence or label. Absent values stay None with a reason.
    """
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    consent = session.consent
    if consent is None or consent.withdrawn_at is not None:
        raise SessionError(409, "Consent is missing or was withdrawn; no combined record can be created.")
    if session.status not in INTEGRATION_STATUSES:
        raise SessionError(409, f"A {session.status.replace('_', ' ')} session cannot be integrated.")

    chosen: dict[str, object] = {}
    modality_status: dict[str, str] = {}
    for modality in MODALITY_ORDER:
        if not getattr(consent, CONSENT_FIELD[modality]):
            modality_status[modality] = "not_consented"
            continue
        items = _measurements(session, modality)
        reliable = [m for m in items if m.is_reliable]
        if reliable:
            chosen[modality] = max(reliable, key=lambda m: (m.captured_at, m.id))
            modality_status[modality] = "used"
        else:
            modality_status[modality] = "excluded_low_quality" if items else "missing"

    if not chosen:
        raise SessionError(
            422,
            "Insufficient data for a combined record: no consented modality has a measurement that passed "
            "its quality checks. Capture again with better lighting, framing or a quieter room.",
        )

    features = []
    for index, (modality, key) in enumerate(INTEGRATION_FEATURES):
        s = spec(modality, key)
        m = chosen.get(modality)
        value = m.features.get(key) if m is not None else None
        status = modality_status[modality] if m is None else ("measured" if value is not None else "not_measured")
        features.append({
            "index": index, "modality": modality, "key": key, "label": s.label, "unit": s.unit,
            "provenance": s.provenance, "value": value, "status": status,
            "measurement_id": m.id if m is not None else None,
        })
    sources = [
        {
            "modality": modality, "measurement_id": m.id, "captured_at": m.captured_at.isoformat() + "Z",
            "source": m.source, "quality_score": m.quality_score, "feature_schema_version": m.feature_schema_version,
            "extractor_version": m.extractor_version,
        }
        for modality, m in chosen.items()
    ]
    consented = [mod for mod in MODALITY_ORDER if modality_status[mod] != "not_consented"]
    record = CombinedResult(
        session_id=session.id,
        mode="feature_integration",
        processing_status="complete" if all(modality_status[m] == "used" for m in consented) else "partial",
        modalities_used=list(chosen),
        indicator_score=None,
        indicator_level=None,
        confidence=None,
        data_quality=None,
        explanation={
            "method": "Latest quality-checked measurement per consented modality, placed in a fixed feature "
            "order. Values are copied as measured; nothing is weighted, combined or scored.",
            "modality_status": modality_status,
        },
        limitations=LIMITATIONS,
        feature_schema_version=integration_schema_label(chosen.values()),
        extractor_version=INTEGRATION_VERSION,
        features=features,
        source_measurements=sources,
    )
    db.add(record)
    db.flush()
    audit.record(
        db, "analysis.integration_recorded", admin_id=admin.id, entity_type="analysis_session", entity_id=session.id,
        details={"result_id": record.id, "processing_status": record.processing_status, "modalities": list(chosen)},
        ip_address=ip,
    )
    db.commit()
    db.refresh(record)
    return record


def integration_schema_label(measurements) -> str:
    """Schema label of a combined record, taken from its inputs rather than the current constant.

    Inputs captured under different feature schemas are labelled "mixed"; each input's own version
    stays in source_measurements.
    """
    versions = {m.feature_schema_version for m in measurements}
    return versions.pop() if len(versions) == 1 else MIXED_SCHEMAS


def list_integrations(db: Session, session_id: int) -> list[CombinedResult]:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise SessionError(404, "Analysis session not found.")
    return sorted(
        (r for r in session.combined_results if r.mode == "feature_integration"),
        key=lambda r: (r.created_at, r.id),
        reverse=True,
    )


# ---- Individual measurement deletion ----------------------------------------------------------

MEASUREMENT_MODELS = {"face": FacialMeasurement, "motion": MotionMeasurement, "voice": VoiceMeasurement}


def delete_measurement(
    db: Session, admin: Admin, session_id: int, modality: str, measurement_id: int, ip: str | None
) -> list[int]:
    """Delete one measurement of this session and every saved combined record that used it.

    Combined records copy values from their source measurements, so a record whose source is
    deleted would no longer match stored data; it is removed in the same transaction.
    Returns the ids of the combined records that were removed.
    """
    model = MEASUREMENT_MODELS[modality]
    measurement = db.get(model, measurement_id)
    if measurement is None or measurement.session_id != session_id:
        raise SessionError(404, "Measurement not found in this session.")
    dependent = [
        r for r in db.query(CombinedResult).filter(CombinedResult.session_id == session_id).all()
        if any(s.get("modality") == modality and s.get("measurement_id") == measurement_id
               for s in (r.source_measurements or []))
    ]
    removed = [r.id for r in dependent]
    try:
        for r in dependent:
            db.delete(r)
        db.delete(measurement)
        audit.record(
            db, "measurement.deleted", admin_id=admin.id, entity_type="analysis_session", entity_id=session_id,
            details={"modality": modality, "measurement_id": measurement_id, "removed_combined_records": removed},
            ip_address=ip,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return removed
