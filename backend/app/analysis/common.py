import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


class FeatureError(ValueError):
    """Input that cannot be measured. The message is safe to show to the user."""


@dataclass
class ExtractionResult:
    features: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    is_reliable: bool = False


def clean(value: float | np.floating | None, digits: int = 4) -> float | None:
    """JSON-safe rounded float; NaN/inf become None (shown as 'not measured')."""
    if value is None:
        return None
    v = float(value)
    return round(v, digits) if math.isfinite(v) else None


def clamp01(value: float) -> float:
    return float(min(1.0, max(0.0, value)))
