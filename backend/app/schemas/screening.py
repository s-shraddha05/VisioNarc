from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UTCDateTime

ModelStatus = Literal["synthetic_demo", "experimental", "validated", "unavailable", "insufficient_input"]


class ScreeningResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    combined_result_id: int
    model_name: str
    model_version: str
    model_status: ModelStatus
    is_synthetic: bool
    target_definition: str
    feature_schema_version: str | None
    input_measurement_ids: dict[str, Any]
    modality_status: dict[str, Any]
    missing_modalities: list[str]
    coverage: float | None
    # Only set for synthetic demo sessions; a hand-set formula, not a probability about a person.
    estimate: float | None
    classification: str | None
    decision_threshold: float | None
    explanation: dict[str, Any]
    limitations: list[str]
    created_at: UTCDateTime


class ScreeningOverview(BaseModel):
    """What the combined-results page shows: whether screening can run here, and saved results."""

    model_config = ConfigDict(protected_namespaces=())

    mode: Literal["off", "synthetic_demo"]
    session_is_synthetic: bool
    can_run: bool
    # For real sessions this is always "unavailable": no validated model exists.
    model_status: ModelStatus
    message: str
    results: list[ScreeningResultOut]
