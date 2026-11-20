from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow

MODEL_TYPES = ("experimental_heuristic", "trained_model")


class ModelVersion(Base):
    """Which scoring method produced a combined result, and how (or whether) it was evaluated."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
        CheckConstraint(
            "model_type IN ('experimental_heuristic', 'trained_model')", name="model_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(32))
    model_type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    feature_schema_version: Mapped[str] = mapped_column(String(16))
    # Evaluation metrics (accuracy, F1, dataset description...). NULL = never evaluated.
    metrics: Mapped[dict[str, Any] | None]
    is_active: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
