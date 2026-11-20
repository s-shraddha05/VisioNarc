"""Request/response models for Phase 3 analysis. Browser-submitted values are strictly range-checked."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import UTCDateTime

Unit = Annotated[float, Field(ge=0.0, le=1.0)]
Coord3 = Annotated[list[float], Field(min_length=3, max_length=3)]
Coord4 = Annotated[list[float], Field(min_length=4, max_length=4)]

_strict = ConfigDict(extra="forbid", allow_inf_nan=False)


class PixelStats(BaseModel):
    """Computed in the browser from the image (see frontend/src/lib/faceStats.ts)."""

    model_config = _strict

    brightness_mean: float = Field(ge=0, le=255)
    contrast_std: float = Field(ge=0, le=128)
    sharpness_laplacian_var: float = Field(ge=0, le=100_000)
    eye_redness_image_left: Unit | None = None
    eye_redness_image_right: Unit | None = None
    pupil_to_iris_ratio_image_left: Unit | None = None
    pupil_to_iris_ratio_image_right: Unit | None = None


class FaceSubmission(BaseModel):
    model_config = _strict

    source: Literal["webcam", "upload"]
    image_width: int = Field(ge=320, le=10_000)
    image_height: int = Field(ge=240, le=10_000)
    landmarks: list[Coord3] = Field(min_length=478, max_length=478)
    pixel_stats: PixelStats
    expressions: dict[str, Unit] = Field(default_factory=dict, max_length=64)

    @field_validator("landmarks")
    @classmethod
    def landmarks_in_frame(cls, value: list[list[float]]) -> list[list[float]]:
        for x, y, z in value:
            if not (-0.25 <= x <= 1.25 and -0.25 <= y <= 1.25 and -1.0 <= z <= 1.0):
                raise ValueError("Face landmarks must be normalised image coordinates (x, y about 0–1).")
        return value


class PoseFrame(BaseModel):
    model_config = _strict

    t_ms: float = Field(ge=0, le=120_000)
    # 33 BlazePose landmarks as [x, y, z, visibility]; null when no person was detected in the frame.
    landmarks: list[Coord4] | None = Field(default=None, min_length=33, max_length=33)

    @field_validator("landmarks")
    @classmethod
    def landmark_ranges(cls, value: list[list[float]] | None) -> list[list[float]] | None:
        if value is None:
            return value
        for x, y, z, v in value:
            if not (-1.0 <= x <= 2.0 and -1.0 <= y <= 2.0 and -10.0 <= z <= 10.0 and 0.0 <= v <= 1.0):
                raise ValueError("Pose landmarks out of range (x, y normalised; visibility 0–1).")
        return value


class MotionSubmission(BaseModel):
    model_config = _strict

    source: Literal["webcam", "upload"]
    video_width: int = Field(ge=160, le=10_000)
    video_height: int = Field(ge=120, le=10_000)
    frames: list[PoseFrame] = Field(min_length=10, max_length=1200)

    @field_validator("frames")
    @classmethod
    def increasing_time(cls, frames: list[PoseFrame]) -> list[PoseFrame]:
        times = [f.t_ms for f in frames]
        if any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("Frame timestamps must be strictly increasing.")
        return frames


class FeatureValue(BaseModel):
    key: str
    label: str
    unit: str
    value: Any
    provenance: str
    provenance_label: str


class ModalitySummary(BaseModel):
    modality: Literal["face", "motion", "voice"]
    status: Literal["available", "low_quality", "missing", "not_consented", "consent_withdrawn"]
    status_reason: str
    measurement_count: int
    measurement_id: int | None
    captured_at: UTCDateTime | None
    source: str | None
    quality_score: float | None
    is_reliable: bool | None
    warnings: list[str]
    key_features: list[FeatureValue]


class MultimodalSummary(BaseModel):
    """Side-by-side view of measured features. Deliberately contains no score or classification."""

    session_id: int
    reference_code: str
    session_status: str
    generated_at: UTCDateTime
    feature_schema_version: str
    available_modalities: list[str]
    missing_modalities: list[str]
    modalities: list[ModalitySummary]
    limitations: list[str]
    method_sources: dict[str, str]
