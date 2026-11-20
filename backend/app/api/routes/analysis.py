from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.analysis.common import FeatureError
from app.analysis.face import extract_face_features
from app.analysis.face import EXTRACTOR_VERSION as FACE_EXTRACTOR
from app.analysis.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    INTEGRATION_FEATURES,
    INTEGRATION_VERSION,
    LIMITATIONS,
    PROVENANCE_LABELS,
    SOURCES,
    catalogue,
)
from app.analysis.motion import EXTRACTOR_VERSION as MOTION_EXTRACTOR
from app.analysis.voice import EXTRACTOR_VERSION as VOICE_EXTRACTOR
from app.analysis.motion import extract_motion_features
from app.analysis.voice import MAX_BYTES, SAMPLE_RATE, decode_wav, extract_voice_features
from app.api.deps import AppSettings, CurrentAdmin, DbSession, client_ip
from app.schemas.analysis import FaceSubmission, MotionSubmission, MultimodalSummary
from app.schemas.screening import ScreeningOverview, ScreeningResultOut
from app.schemas.sessions import (
    CombinedResultOut,
    FacialMeasurementOut,
    MotionMeasurementOut,
    SessionDetail,
    VoiceMeasurementOut,
)
from app.services import analysis_service, screening_service, session_service
from app.services.session_service import SessionError

router = APIRouter(prefix="/sessions", tags=["analysis"])
schema_router = APIRouter(prefix="/analysis", tags=["analysis"])

WAV_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"}


def _http(exc: SessionError | FeatureError) -> HTTPException:
    if isinstance(exc, SessionError):
        return HTTPException(exc.status_code, exc.detail)
    return HTTPException(422, str(exc))


@router.post("/{session_id}/analysis/face", response_model=FacialMeasurementOut, status_code=201)
def analyze_face(session_id: int, body: FaceSubmission, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        session = analysis_service.session_for_capture(db, session_id, "face")
        result = extract_face_features(
            np.asarray(body.landmarks, dtype=float),
            body.image_width,
            body.image_height,
            body.pixel_stats.model_dump(),
            body.expressions,
        )
    except (SessionError, FeatureError) as exc:
        raise _http(exc) from None
    return analysis_service.record_face(db, admin, session, body, result, client_ip(request))


@router.post("/{session_id}/analysis/motion", response_model=MotionMeasurementOut, status_code=201)
def analyze_motion(session_id: int, body: MotionSubmission, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        session = analysis_service.session_for_capture(db, session_id, "motion")
        times, landmarks = analysis_service.motion_arrays(body)
        result = extract_motion_features(times, landmarks, body.video_width, body.video_height)
    except (SessionError, FeatureError) as exc:
        raise _http(exc) from None
    return analysis_service.record_motion(db, admin, session, body, result, client_ip(request))


@router.post("/{session_id}/analysis/voice", response_model=VoiceMeasurementOut, status_code=201)
async def analyze_voice(
    session_id: int,
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    source: Annotated[Literal["microphone", "upload"], Query()],
    upload_consent: Annotated[bool, Query()] = False,
):
    """Body: raw 16 kHz mono 16-bit PCM WAV (Content-Type: audio/wav), at most 4 MB.

    The audio is read into memory, measured, and discarded. It is never written to disk,
    stored in the database, or logged.
    """
    if not upload_consent:
        raise HTTPException(400, "Explicit confirmation to upload this recording is required (upload_consent=true).")
    try:
        session = analysis_service.session_for_capture(db, session_id, "voice")
    except SessionError as exc:
        raise _http(exc) from None
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in WAV_TYPES:
        raise HTTPException(415, "Send the recording as audio/wav.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
        raise HTTPException(413, "Recording exceeds the 4 MB limit.")

    buffer = bytearray()
    async for chunk in request.stream():
        buffer.extend(chunk)
        if len(buffer) > MAX_BYTES:
            raise HTTPException(413, "Recording exceeds the 4 MB limit.")
    try:
        samples = decode_wav(bytes(buffer))
        result = await run_in_threadpool(extract_voice_features, samples)
    except FeatureError as exc:
        raise _http(exc) from None
    finally:
        buffer.clear()
    return analysis_service.record_voice(db, admin, session, source, result, SAMPLE_RATE, client_ip(request))


@router.get("/{session_id}/multimodal-summary", response_model=MultimodalSummary)
def multimodal_summary(session_id: int, db: DbSession, _admin: CurrentAdmin):
    try:
        return analysis_service.multimodal_summary(db, session_id)
    except SessionError as exc:
        raise _http(exc) from None


@router.post("/{session_id}/integrations", response_model=CombinedResultOut, status_code=201)
def create_integration(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    """Save a score-free, ordered record of this session's quality-checked measurements."""
    try:
        return analysis_service.create_integration(db, admin, session_id, client_ip(request))
    except SessionError as exc:
        raise _http(exc) from None


@router.get("/{session_id}/integrations", response_model=list[CombinedResultOut])
def list_integrations(session_id: int, db: DbSession, _admin: CurrentAdmin):
    try:
        return analysis_service.list_integrations(db, session_id)
    except SessionError as exc:
        raise _http(exc) from None


@router.get("/{session_id}/screening", response_model=ScreeningOverview)
def screening_overview(session_id: int, db: DbSession, settings: AppSettings, _admin: CurrentAdmin):
    """Whether experimental screening can run for this session, and its saved results.

    Real sessions always report "unavailable": there is no validated model.
    """
    try:
        return screening_service.overview(db, session_id, settings)
    except SessionError as exc:
        raise _http(exc) from None


@router.post("/{session_id}/screening", response_model=ScreeningResultOut, status_code=201)
def run_screening(session_id: int, request: Request, db: DbSession, settings: AppSettings, admin: CurrentAdmin):
    """Run the synthetic demonstration formula on the latest saved combined record and store it.

    Only for sessions created by scripts.seed_synthetic_demo, and only with SCREENING_MODE=synthetic_demo.
    """
    try:
        return screening_service.run(db, admin, session_id, settings, client_ip(request))
    except SessionError as exc:
        raise _http(exc) from None


class MeasurementDeleted(BaseModel):
    modality: Literal["face", "motion", "voice"]
    measurement_id: int
    removed_combined_records: list[int]


@router.delete("/{session_id}/measurements/{modality}/{measurement_id}", response_model=MeasurementDeleted)
def delete_measurement(
    session_id: int,
    modality: Literal["face", "motion", "voice"],
    measurement_id: int,
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
):
    try:
        removed = analysis_service.delete_measurement(db, admin, session_id, modality, measurement_id, client_ip(request))
    except SessionError as exc:
        raise _http(exc) from None
    return MeasurementDeleted(modality=modality, measurement_id=measurement_id, removed_combined_records=removed)


@router.post("/{session_id}/complete", response_model=SessionDetail)
def complete(session_id: int, request: Request, db: DbSession, admin: CurrentAdmin):
    try:
        analysis_service.complete_session(db, admin, session_id, client_ip(request))
        return session_service.get_detail(db, session_id)
    except SessionError as exc:
        raise _http(exc) from None


@schema_router.get("/feature-schema")
def feature_schema(_admin: CurrentAdmin):
    return {
        "version": FEATURE_SCHEMA_VERSION,
        "provenance": PROVENANCE_LABELS,
        "features": catalogue(),
        "limitations": LIMITATIONS,
        "sources": SOURCES,
        "extractors": {"face": FACE_EXTRACTOR, "motion": MOTION_EXTRACTOR, "voice": VOICE_EXTRACTOR},
        "integration": {
            "version": INTEGRATION_VERSION,
            "feature_order": [f"{m}.{k}" for m, k in INTEGRATION_FEATURES],
        },
    }
