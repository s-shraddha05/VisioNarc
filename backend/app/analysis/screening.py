"""Synthetic screening demonstration: a fixed, documented formula over the 14 integration features.

THIS IS NOT A TRAINED OR VALIDATED MODEL. No labelled dataset with independent reference outcomes
exists for VisoNarc (see docs/BUILD_STATUS.md, Phase 5 dataset audit). The weights below were
chosen by hand to exercise the software workflow; they encode no scientific finding, and the
score says nothing about any real person. The service only runs it for sessions flagged
is_synthetic, and only when SCREENING_MODE=synthetic_demo.

Rules:
* Inputs come from one saved feature-integration record (14 features in a fixed order).
* Names, order, schema version and plausible ranges are validated; any failure -> no score.
* Missing modalities stay missing (never zero-filled); at least MIN_MODALITIES must be measured.
* score = sigmoid(BIAS + sum(weight * (value - centre) / scale)) over the weighted features present.
"""

import math
from dataclasses import dataclass, field

from app.analysis.feature_schema import FEATURE_SCHEMA_VERSION, INTEGRATION_FEATURES

MODEL_NAME = "visonarc-synthetic-demo"
MODEL_VERSION = "demo/1.0.0+hand-set-weights"
TARGET_DEFINITION = (
    "None. Synthetic demonstration only: there is no reference outcome. The score and label are "
    "illustrative outputs of a hand-set formula on synthetic data and are not a probability of drug "
    "use, addiction, exposure or impairment for any person."
)
DEMO_LABEL_POSITIVE = "Addict"
DEMO_LABEL_NEGATIVE = "Non-Addict"
DECISION_THRESHOLD = 0.5
MIN_MODALITIES = 2
BIAS = 0.0
LIMITATIONS = [
    "Synthetic demonstration: the formula's weights were set by hand, not learned from data.",
    "No labelled dataset with independent reference outcomes (e.g. toxicology) was available.",
    "The score is not a probability about a real person and must not be used for any decision.",
    "Facial appearance, voice and movement cannot by themselves establish drug use or impairment.",
]

# (modality, key): (plausible_min, plausible_max, centre, scale, weight). weight 0 = validated, unweighted
# (image, tracking and recording quality features are checked but never scored).
DEMO_FEATURES: dict[tuple[str, str], tuple[float, float, float, float, float]] = {
    ("face", "ear_mean"): (0.0, 0.6, 0.28, 0.05, -0.8),
    ("face", "symmetry_index"): (0.0, 1.0, 0.95, 0.05, -0.6),
    ("face", "brightness_mean"): (0.0, 255.0, 0.0, 1.0, 0.0),
    ("face", "sharpness_laplacian_var"): (0.0, 1e7, 0.0, 1.0, 0.0),
    ("motion", "tracked_fraction"): (0.0, 1.0, 0.0, 1.0, 0.0),
    ("motion", "mean_speed_bw_s"): (0.0, 50.0, 0.5, 0.5, 0.5),
    ("motion", "movement_variability_cv"): (0.0, 50.0, 0.5, 0.5, 0.6),
    ("motion", "dominant_frequency_hz"): (0.0, 15.0, 1.0, 1.5, 0.3),
    ("motion", "shoulder_tilt_deg_std"): (0.0, 90.0, 2.0, 2.0, 0.7),
    ("voice", "snr_db_estimate"): (-30.0, 120.0, 0.0, 1.0, 0.0),
    ("voice", "active_fraction"): (0.0, 1.0, 0.0, 1.0, 0.0),
    ("voice", "f0_median_hz"): (40.0, 600.0, 160.0, 60.0, 0.0),
    ("voice", "f0_std_semitones"): (0.0, 24.0, 2.0, 1.5, -0.5),
    ("voice", "spectral_centroid_hz"): (0.0, 8000.0, 1500.0, 600.0, 0.4),
}
assert list(DEMO_FEATURES) == list(INTEGRATION_FEATURES), "demo constants must follow the integration order"


@dataclass
class ScreeningOutcome:
    model_status: str  # "synthetic_demo" or "insufficient_input"
    estimate: float | None
    classification: str | None
    coverage: float | None
    missing_modalities: list[str]
    reasons: list[str] = field(default_factory=list)
    contributions: list[dict] = field(default_factory=list)


def _insufficient(missing: list[str], reasons: list[str]) -> ScreeningOutcome:
    return ScreeningOutcome("insufficient_input", None, None, None, missing, reasons)


def score(features: list[dict], feature_schema_version: str | None, modality_status: dict[str, str]) -> ScreeningOutcome:
    """Validate a saved integration record's features and apply the demo formula (pure function)."""
    modalities = sorted({m for m, _ in INTEGRATION_FEATURES})
    missing = [m for m in modalities if modality_status.get(m) != "used"]
    if [(f.get("modality"), f.get("key")) for f in features] != list(INTEGRATION_FEATURES):
        return _insufficient(missing, ["Feature names or order do not match the integration schema."])
    if feature_schema_version != FEATURE_SCHEMA_VERSION:
        return _insufficient(missing, [
            f"Feature schema {feature_schema_version or 'unknown'} is not supported; the demo formula is "
            f"defined for schema {FEATURE_SCHEMA_VERSION} only."
        ])
    if len(modalities) - len(missing) < MIN_MODALITIES:
        return _insufficient(missing, [
            f"At least {MIN_MODALITIES} of {len(modalities)} modalities must have a quality-checked measurement."
        ])

    invalid, contributions, z, weighted_total, weighted_present = [], [], BIAS, 0, 0
    for f in features:
        lo, hi, centre, scale, weight = DEMO_FEATURES[(f["modality"], f["key"])]
        weighted_total += weight != 0
        value = f.get("value")
        if f["modality"] in missing or value is None:
            continue  # missing stays missing: no imputation
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            invalid.append(f"{f['modality']}.{f['key']}")
            continue
        if weight:
            term = weight * (value - centre) / scale
            z += term
            weighted_present += 1
            contributions.append({"feature": f"{f['modality']}.{f['key']}", "value": value, "contribution": round(term, 4)})
    if invalid:
        return _insufficient(missing, [f"Values outside the plausible range or not numeric: {', '.join(invalid)}."])
    if weighted_present == 0:
        return _insufficient(missing, ["None of the scored features were measured."])

    estimate = round(1.0 / (1.0 + math.exp(-z)), 4)
    label = DEMO_LABEL_POSITIVE if estimate >= DECISION_THRESHOLD else DEMO_LABEL_NEGATIVE
    return ScreeningOutcome(
        "synthetic_demo", estimate, label, round(weighted_present / weighted_total, 4), missing, [], contributions
    )
