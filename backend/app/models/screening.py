"""Stored screening results (migration 0003). Separate from raw measurements and combined records.

Only the synthetic demonstration writes rows here, and only for sessions flagged is_synthetic.
There is no validated model: real sessions never receive an estimate or a classification.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

MODEL_STATUSES = ("synthetic_demo", "experimental", "validated", "unavailable", "insufficient_input")


class ScreeningResult(Base):
    __tablename__ = "screening_results"
    __table_args__ = (
        CheckConstraint(f"model_status IN ({', '.join(repr(s) for s in MODEL_STATUSES)})", name="model_status"),
        CheckConstraint("estimate IS NULL OR (estimate >= 0 AND estimate <= 1)", name="estimate"),
        CheckConstraint("coverage IS NULL OR (coverage >= 0 AND coverage <= 1)", name="coverage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    # The saved feature-integration record this result was computed from (its inputs and versions).
    combined_result_id: Mapped[int] = mapped_column(
        ForeignKey("combined_results.id", ondelete="CASCADE"), index=True
    )
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(64))
    model_status: Mapped[str] = mapped_column(String(24))
    is_synthetic: Mapped[bool]
    target_definition: Mapped[str] = mapped_column(Text)
    feature_schema_version: Mapped[str | None] = mapped_column(String(16))
    input_measurement_ids: Mapped[dict[str, Any]]
    modality_status: Mapped[dict[str, Any]]
    missing_modalities: Mapped[list[str]]
    coverage: Mapped[float | None]
    estimate: Mapped[float | None]
    classification: Mapped[str | None] = mapped_column(String(32))
    decision_threshold: Mapped[float | None]
    explanation: Mapped[dict[str, Any]]
    limitations: Mapped[list[str]]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    session: Mapped["AnalysisSession"] = relationship(back_populates="screening_results")  # noqa: F821
    combined_result: Mapped["CombinedResult"] = relationship(back_populates="screening_results")  # noqa: F821
