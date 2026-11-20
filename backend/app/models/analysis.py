"""Analysis sessions, consent, per-modality measurements and combined results.

Measurements store extracted features only (JSON, versioned by feature_schema_version).
Raw media is not stored unless STORE_RAW_MEDIA is enabled and the subject consented.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow

SESSION_STATUSES = ("draft", "consented", "in_progress", "completed", "failed", "cancelled")
CAPTURE_SOURCES = ("webcam", "upload", "microphone")
# "feature_integration" (migration 0002) stores an ordered, provenance-tagged feature record with
# no score; the other two modes are reserved and unused.
RESULT_MODES = ("experimental_heuristic", "trained_model", "feature_integration")
PROCESSING_STATUSES = ("complete", "partial")
INDICATOR_LEVELS = ("low", "moderate", "elevated", "insufficient_data")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _unit_interval(column: str) -> str:
    return f"{column} IS NULL OR ({column} >= 0 AND {column} <= 1)"


class AnalysisSession(TimestampMixin, Base):
    __tablename__ = "analysis_sessions"
    __table_args__ = (CheckConstraint(_in_list("status", SESSION_STATUSES), name="status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_code: Mapped[str] = mapped_column(String(32), unique=True)
    # Pseudonymous label chosen by the admin; no real names are required.
    subject_label: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), index=True
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None]
    retain_until: Mapped[datetime | None] = mapped_column(index=True)
    # Migration 0003. Set only by scripts.seed_synthetic_demo; the API never sets it.
    is_synthetic: Mapped[bool] = mapped_column(default=False, server_default=text("0"))

    consent: Mapped["ConsentRecord | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    facial_measurements: Mapped[list["FacialMeasurement"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    motion_measurements: Mapped[list["MotionMeasurement"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    voice_measurements: Mapped[list["VoiceMeasurement"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    combined_results: Mapped[list["CombinedResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    screening_results: Mapped[list["ScreeningResult"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"), unique=True
    )
    consent_given: Mapped[bool]
    consent_text_version: Mapped[str] = mapped_column(String(16))
    consented_by_label: Mapped[str] = mapped_column(String(100))
    allow_face: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    allow_motion: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    allow_voice: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    allow_raw_media_storage: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    recorded_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL")
    )
    consented_at: Mapped[datetime] = mapped_column(default=utcnow)
    withdrawn_at: Mapped[datetime | None]

    session: Mapped[AnalysisSession] = relationship(back_populates="consent")


class MeasurementMixin:
    """Columns shared by facial, motion and voice measurements."""

    id: Mapped[int] = mapped_column(primary_key=True)

    @declared_attr
    def session_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)

    source: Mapped[str] = mapped_column(String(20))
    quality_score: Mapped[float | None]
    is_reliable: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    feature_schema_version: Mapped[str] = mapped_column(String(16))
    # Version of the server-side extractor (and the expected browser pipeline) that produced the
    # features. NULL for rows created before migration 0002, where it was not recorded.
    extractor_version: Mapped[str | None] = mapped_column(String(64))
    features: Mapped[dict[str, Any]]
    warnings: Mapped[list[str]] = mapped_column(default=list)
    captured_at: Mapped[datetime] = mapped_column(default=utcnow)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


def _measurement_checks() -> tuple[CheckConstraint, CheckConstraint]:
    return (
        CheckConstraint(_in_list("source", CAPTURE_SOURCES), name="source"),
        CheckConstraint(_unit_interval("quality_score"), name="quality_score"),
    )


class FacialMeasurement(MeasurementMixin, Base):
    __tablename__ = "facial_measurements"
    __table_args__ = _measurement_checks()

    image_width: Mapped[int | None]
    image_height: Mapped[int | None]
    face_detected: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    brightness: Mapped[float | None]
    sharpness: Mapped[float | None]

    session: Mapped[AnalysisSession] = relationship(back_populates="facial_measurements")


class MotionMeasurement(MeasurementMixin, Base):
    __tablename__ = "motion_measurements"
    __table_args__ = _measurement_checks()

    duration_seconds: Mapped[float | None]
    frames_processed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    frames_with_pose: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    session: Mapped[AnalysisSession] = relationship(back_populates="motion_measurements")


class VoiceMeasurement(MeasurementMixin, Base):
    __tablename__ = "voice_measurements"
    __table_args__ = _measurement_checks()

    duration_seconds: Mapped[float | None]
    sample_rate: Mapped[int | None]
    snr_db: Mapped[float | None]

    session: Mapped[AnalysisSession] = relationship(back_populates="voice_measurements")


class CombinedResult(Base):
    """Combined record for a session. Never a diagnosis or proof of drug use.

    Only mode "feature_integration" is written: an ordered list of measured features with
    provenance, built from the session's own reliable measurements. Its indicator_score,
    indicator_level and confidence are always NULL — VisoNarc produces no score or label.
    """

    __tablename__ = "combined_results"
    __table_args__ = (
        CheckConstraint(_in_list("mode", RESULT_MODES), name="mode"),
        CheckConstraint(
            f"processing_status IS NULL OR {_in_list('processing_status', PROCESSING_STATUSES)}",
            name="processing_status",
        ),
        CheckConstraint(_in_list("indicator_level", INDICATOR_LEVELS), name="indicator_level"),
        CheckConstraint(_unit_interval("indicator_score"), name="indicator_score"),
        CheckConstraint(_unit_interval("confidence"), name="confidence"),
        CheckConstraint(_unit_interval("data_quality"), name="data_quality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(String(32))
    modalities_used: Mapped[list[str]]
    indicator_score: Mapped[float | None]
    indicator_level: Mapped[str | None] = mapped_column(String(20))  # NULL passes the IN check
    confidence: Mapped[float | None]
    data_quality: Mapped[float | None]
    explanation: Mapped[dict[str, Any]]
    limitations: Mapped[list[str]]
    # Added in migration 0002 for feature_integration records.
    processing_status: Mapped[str | None] = mapped_column(String(20))
    feature_schema_version: Mapped[str | None] = mapped_column(String(16))
    extractor_version: Mapped[str | None] = mapped_column(String(64))
    features: Mapped[list[Any] | None]
    source_measurements: Mapped[list[Any] | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    session: Mapped[AnalysisSession] = relationship(back_populates="combined_results")
    screening_results: Mapped[list["ScreeningResult"]] = relationship(  # noqa: F821
        back_populates="combined_result", cascade="all, delete-orphan", passive_deletes=True
    )
