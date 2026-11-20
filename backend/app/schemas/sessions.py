from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import UTCDateTime
from app.schemas.screening import ScreeningResultOut

SessionStatus = Literal["draft", "consented", "in_progress", "completed", "failed", "cancelled"]

# Version of the consent wording shown in the New Analysis page (frontend/src/lib/consent.ts).
CONSENT_TEXT_VERSION = "1.0"


def _clean_label(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("must not be blank")
    return value


class ConsentIn(BaseModel):
    consent_given: Literal[True] = Field(
        description="Must be true; an analysis session cannot be created without consent."
    )
    consented_by_label: str = Field(min_length=1, max_length=100)
    allow_face: bool = False
    allow_motion: bool = False
    allow_voice: bool = False
    allow_raw_media_storage: bool = False

    _clean = field_validator("consented_by_label")(_clean_label)

    @model_validator(mode="after")
    def at_least_one_modality(self) -> "ConsentIn":
        if not (self.allow_face or self.allow_motion or self.allow_voice):
            raise ValueError("Consent must allow at least one modality (face, motion or voice).")
        return self


class SessionCreate(BaseModel):
    subject_label: str = Field(
        min_length=1,
        max_length=100,
        description="Pseudonymous label, e.g. 'Participant 07'. Avoid real names.",
    )
    notes: str | None = Field(default=None, max_length=2000)
    consent: ConsentIn

    _clean = field_validator("subject_label")(_clean_label)

    @field_validator("notes")
    @classmethod
    def blank_notes_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consent_given: bool
    consent_text_version: str
    consented_by_label: str
    allow_face: bool
    allow_motion: bool
    allow_voice: bool
    allow_raw_media_storage: bool
    consented_at: UTCDateTime
    withdrawn_at: UTCDateTime | None


class MeasurementCounts(BaseModel):
    face: int
    motion: int
    voice: int
    results: int


class SessionSummary(BaseModel):
    id: int
    reference_code: str
    subject_label: str
    status: SessionStatus
    created_at: UTCDateTime
    updated_at: UTCDateTime
    completed_at: UTCDateTime | None
    retain_until: UTCDateTime | None
    created_by: str | None
    allow_face: bool
    allow_motion: bool
    allow_voice: bool
    consent_withdrawn: bool
    counts: MeasurementCounts
    # Created by scripts.seed_synthetic_demo; never a real person.
    is_synthetic: bool


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    quality_score: float | None
    is_reliable: bool
    feature_schema_version: str
    extractor_version: str | None  # None = recorded before migration 0002
    features: dict[str, Any]
    warnings: list[str]
    captured_at: UTCDateTime


class FacialMeasurementOut(MeasurementOut):
    image_width: int | None
    image_height: int | None
    face_detected: bool
    brightness: float | None
    sharpness: float | None


class MotionMeasurementOut(MeasurementOut):
    duration_seconds: float | None
    frames_processed: int
    frames_with_pose: int


class VoiceMeasurementOut(MeasurementOut):
    duration_seconds: float | None
    sample_rate: int | None
    snr_db: float | None


class CombinedResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    processing_status: str | None
    modalities_used: list[str]
    # Always None for feature_integration records: VisoNarc produces no score or label.
    indicator_score: float | None
    indicator_level: str | None
    confidence: float | None
    data_quality: float | None
    explanation: dict[str, Any]
    limitations: list[str]
    feature_schema_version: str | None
    extractor_version: str | None
    features: list[dict[str, Any]] | None
    source_measurements: list[dict[str, Any]] | None
    model_version_id: int | None
    created_at: UTCDateTime


class SessionDetail(SessionSummary):
    notes: str | None
    consent: ConsentOut | None
    facial_measurements: list[FacialMeasurementOut]
    motion_measurements: list[MotionMeasurementOut]
    voice_measurements: list[VoiceMeasurementOut]
    combined_results: list[CombinedResultOut]
    screening_results: list[ScreeningResultOut]


class SessionExport(BaseModel):
    """Downloadable session record (the Reports page 'JSON record')."""

    app: str
    report_type: Literal["session_record"] = "session_record"
    generated_at: UTCDateTime
    generated_by: str
    disclaimer: str
    session: SessionDetail
