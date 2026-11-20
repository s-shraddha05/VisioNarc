"""Catalogue of every stored feature: label, unit, where it was computed, and method source.

FEATURE_SCHEMA_VERSION is stored with each measurement. Bump it whenever a feature's
definition changes so old and new measurements are never mixed silently.

No reference ranges ("normal" values) are defined anywhere: VisoNarc reports measurements only.
"""

from dataclasses import asdict, dataclass
from typing import Literal

# 1.0 – initial Phase 3 features.
# 1.1 – server withholds browser eye-region/pupil values it cannot support (closed eyes, eye < 20 px,
#       iris < 30 px); motion frames carry actual decoded frame times. Same keys and units.
FEATURE_SCHEMA_VERSION = "1.1"

Provenance = Literal["server_audio", "server_landmarks", "browser_pixels", "browser_model"]

PROVENANCE_LABELS: dict[str, str] = {
    "server_audio": "Computed on the server from the uploaded audio (audio not stored).",
    "server_landmarks": "Computed on the server from landmarks detected in the browser by MediaPipe.",
    "browser_pixels": "Computed in the browser from image pixels. The server checks its range but cannot verify it.",
    "browser_model": "Output of the MediaPipe model running in the browser. Range-checked by the server only.",
}

# Method sources (definitions of how a value is computed — not reference values).
SOURCES: dict[str, str] = {
    "yin": "de Cheveigné, A. & Kawahara, H. (2002). YIN, a fundamental frequency estimator for speech "
    "and music. J. Acoust. Soc. Am. 111(4), 1917–1930.",
    "mfcc": "Davis, S. & Mermelstein, P. (1980). Comparison of parametric representations for monosyllabic "
    "word recognition in continuously spoken sentences. IEEE Trans. ASSP 28(4), 357–366.",
    "ear": "Soukupová, T. & Čech, J. (2016). Real-Time Eye Blink Detection using Facial Landmarks. "
    "21st Computer Vision Winter Workshop.",
    "face_mesh": "Kartynnik, Y. et al. (2019). Real-time Facial Surface Geometry from Monocular Video on "
    "Mobile GPUs. arXiv:1907.06724.",
    "blazepose": "Bazarevsky, V. et al. (2020). BlazePose: On-device Real-time Body Pose tracking. "
    "arXiv:2006.10204.",
}


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    modality: Literal["face", "motion", "voice"]
    label: str
    unit: str
    provenance: Provenance
    description: str
    source: str | None = None
    summary: bool = False  # shown in the multimodal summary


def _f(*args, **kwargs) -> FeatureSpec:
    return FeatureSpec(*args, **kwargs)


FEATURES: list[FeatureSpec] = [
    # ---- voice -----------------------------------------------------------------------------
    _f("duration_s", "voice", "Recording length", "s", "server_audio", "Length of the analysed audio."),
    _f("level_dbfs", "voice", "Overall level", "dBFS", "server_audio", "RMS level relative to digital full scale."),
    _f("snr_db_estimate", "voice", "Signal-to-noise estimate", "dB", "server_audio",
       "90th minus 10th percentile of 25 ms frame levels. A rough estimate; unavailable when no quiet frames exist.",
       summary=True),
    _f("clipping_fraction", "voice", "Clipped samples", "fraction", "server_audio",
       "Share of samples at or above 99.9 % of full scale."),
    _f("active_fraction", "voice", "Sound-active time", "fraction", "server_audio",
       "Share of 25 ms frames above the adaptive level threshold.", summary=True),
    _f("pause_count", "voice", "Pauses", "count", "server_audio", "Quiet stretches of at least 250 ms between active sound."),
    _f("mean_pause_s", "voice", "Mean pause length", "s", "server_audio", "Average length of the detected pauses."),
    _f("active_segments_per_min", "voice", "Active segments per minute", "1/min", "server_audio",
       "Number of continuous active stretches (≥ 100 ms) per minute of recording; a timing proxy, not a syllable rate."),
    _f("voiced_fraction", "voice", "Voiced share of active time", "fraction", "server_audio",
       "Share of active frames in which YIN found a periodic pitch.", "yin"),
    _f("f0_median_hz", "voice", "Pitch (median F0)", "Hz", "server_audio",
       "Median fundamental frequency over voiced frames (YIN, 60–400 Hz search range).", "yin", summary=True),
    _f("f0_mean_hz", "voice", "Pitch (mean F0)", "Hz", "server_audio", "Mean fundamental frequency over voiced frames.", "yin"),
    _f("f0_std_hz", "voice", "Pitch variability", "Hz", "server_audio", "Standard deviation of F0 over voiced frames.", "yin"),
    _f("f0_std_semitones", "voice", "Pitch variability", "semitones", "server_audio",
       "Standard deviation of F0 relative to its median, in semitones.", "yin", summary=True),
    _f("f0_range_semitones", "voice", "Pitch range (5th–95th pct)", "semitones", "server_audio",
       "Distance between the 5th and 95th percentile of F0.", "yin"),
    _f("spectral_centroid_hz", "voice", "Spectral centroid", "Hz", "server_audio",
       "Power-weighted mean frequency of active frames.", summary=True),
    _f("spectral_bandwidth_hz", "voice", "Spectral bandwidth", "Hz", "server_audio", "Power-weighted spread around the centroid."),
    _f("spectral_rolloff_hz", "voice", "Spectral roll-off (85 %)", "Hz", "server_audio",
       "Frequency below which 85 % of the spectral power lies."),
    _f("spectral_flatness", "voice", "Spectral flatness", "0–1", "server_audio",
       "Geometric/arithmetic mean ratio of the power spectrum (1 = noise-like, 0 = tonal)."),
    _f("zero_crossing_rate", "voice", "Zero-crossing rate", "per sample", "server_audio", "Mean sign changes per sample in active frames."),
    _f("mfcc_mean", "voice", "MFCC means (c0–c12)", "13 values", "server_audio",
       "Mean of 13 mel-frequency cepstral coefficients (26 mel bands, 25 ms frames).", "mfcc"),
    # ---- face (single image) ---------------------------------------------------------------
    _f("face_width_fraction", "face", "Face width in image", "fraction", "server_landmarks",
       "Horizontal extent of the face landmarks relative to image width.", "face_mesh"),
    _f("frontal_offset", "face", "Head turn proxy", "fraction", "server_landmarks",
       "Horizontal nose-tip offset from the cheek midpoint, relative to face width (0 = frontal).", "face_mesh"),
    _f("ear_image_left", "face", "Eye aspect ratio (image-left eye)", "ratio", "server_landmarks",
       "Eye aspect ratio from six eyelid/corner landmarks.", "ear"),
    _f("ear_image_right", "face", "Eye aspect ratio (image-right eye)", "ratio", "server_landmarks",
       "Eye aspect ratio from six eyelid/corner landmarks.", "ear"),
    _f("ear_mean", "face", "Eye openness (mean EAR)", "ratio", "server_landmarks",
       "Mean eye aspect ratio of both eyes.", "ear", summary=True),
    _f("ear_asymmetry", "face", "Eye openness asymmetry", "fraction", "server_landmarks",
       "|EAR left − EAR right| / mean EAR.", "ear"),
    _f("mouth_aspect_ratio", "face", "Mouth aspect ratio", "ratio", "server_landmarks", "Inner-lip opening / mouth width."),
    _f("symmetry_index", "face", "Landmark symmetry index", "0–1", "server_landmarks",
       "1 − mean mirrored-pair offset across the facial midline, normalised by inter-ocular distance. "
       "Describes landmark geometry only.", "face_mesh", summary=True),
    _f("iris_diameter_px_image_left", "face", "Iris diameter (image-left)", "px", "server_landmarks",
       "Iris diameter from MediaPipe iris landmarks, in image pixels."),
    _f("iris_diameter_px_image_right", "face", "Iris diameter (image-right)", "px", "server_landmarks",
       "Iris diameter from MediaPipe iris landmarks, in image pixels."),
    _f("iris_to_eye_width_ratio", "face", "Iris / eye width", "ratio", "server_landmarks",
       "Mean iris diameter divided by mean eye width."),
    _f("brightness_mean", "face", "Face brightness", "0–255", "browser_pixels",
       "Mean grey level of the face region.", summary=True),
    _f("contrast_std", "face", "Face contrast", "0–255", "browser_pixels", "Standard deviation of grey levels in the face region."),
    _f("sharpness_laplacian_var", "face", "Sharpness", "variance", "browser_pixels",
       "Variance of the Laplacian of the face region resized to 256 px width.", summary=True),
    _f("eye_redness_image_left", "face", "Eye-region red ratio (image-left)", "0–1", "browser_pixels",
       "Mean R/(R+G+B) inside the eye contour. Strongly affected by lighting and camera white balance."),
    _f("eye_redness_image_right", "face", "Eye-region red ratio (image-right)", "0–1", "browser_pixels",
       "Mean R/(R+G+B) inside the eye contour. Strongly affected by lighting and camera white balance."),
    _f("pupil_to_iris_ratio_image_left", "face", "Dark pupil-region / iris (image-left)", "ratio", "browser_pixels",
       "Equivalent diameter of the darkest region inside the iris divided by iris diameter. Only measured when the "
       "iris is ≥ 30 px wide; webcam images are generally unreliable for pupil size."),
    _f("pupil_to_iris_ratio_image_right", "face", "Dark pupil-region / iris (image-right)", "ratio", "browser_pixels",
       "As above, image-right eye."),
    _f("expression_scores", "face", "Expression coefficients", "0–1 each", "browser_model",
       "Selected MediaPipe blendshape coefficients (eye blink/squint/wide, brow down, jaw open, smile). "
       "These describe facial movement, not emotion or state.", "face_mesh"),
    # ---- motion ------------------------------------------------------------------------------
    _f("duration_s", "motion", "Clip length", "s", "server_landmarks", "Time span of the analysed frames."),
    _f("tracked_fraction", "motion", "Pose tracked", "fraction", "server_landmarks",
       "Share of frames with nose and both shoulders visible (visibility ≥ 0.5).", "blazepose", summary=True),
    _f("mean_speed_bw_s", "motion", "Upper-body speed (mean)", "shoulder widths/s", "server_landmarks",
       "Mean speed of nose, shoulders, elbows and wrists, normalised by median shoulder width.", "blazepose",
       summary=True),
    _f("speed_std_bw_s", "motion", "Upper-body speed (SD)", "shoulder widths/s", "server_landmarks",
       "Standard deviation of the per-frame upper-body speed.", "blazepose"),
    _f("speed_p95_bw_s", "motion", "Upper-body speed (95th pct)", "shoulder widths/s", "server_landmarks",
       "95th percentile of per-frame upper-body speed.", "blazepose"),
    _f("movement_variability_cv", "motion", "Movement variability", "CV", "server_landmarks",
       "Coefficient of variation of per-frame upper-body speed.", "blazepose", summary=True),
    _f("head_speed_bw_s", "motion", "Head speed (mean)", "shoulder widths/s", "server_landmarks", "Mean nose speed.", "blazepose"),
    _f("wrist_speed_bw_s", "motion", "Wrist speed (mean)", "shoulder widths/s", "server_landmarks",
       "Mean speed of both wrists (when visible).", "blazepose"),
    _f("dominant_frequency_hz", "motion", "Dominant movement frequency", "Hz", "server_landmarks",
       "Frequency with most power (0.25–7.5 Hz) in detrended head and wrist position, resampled to 15 Hz.",
       "blazepose", summary=True),
    _f("dominant_power_fraction", "motion", "Periodicity of dominant frequency", "fraction", "server_landmarks",
       "Share of 0.25–7.5 Hz power within ±1 bin of the dominant frequency (higher = more rhythmic)."),
    _f("shoulder_tilt_deg_mean", "motion", "Shoulder tilt (mean)", "degrees", "server_landmarks",
       "Mean absolute angle of the shoulder line from horizontal.", "blazepose"),
    _f("shoulder_tilt_deg_std", "motion", "Shoulder tilt variation", "degrees", "server_landmarks",
       "Standard deviation of shoulder-line angle (posture variation).", "blazepose", summary=True),
    _f("trunk_lean_deg_mean", "motion", "Trunk lean (mean)", "degrees", "server_landmarks",
       "Mean angle of shoulder-mid to hip-mid line from vertical; only when hips are visible.", "blazepose"),
    _f("trunk_lean_deg_std", "motion", "Trunk lean variation", "degrees", "server_landmarks",
       "Standard deviation of trunk angle; only when hips are visible.", "blazepose"),
    _f("head_offset_std_bw", "motion", "Head sway", "shoulder widths", "server_landmarks",
       "Standard deviation of nose position relative to the shoulder midpoint.", "blazepose"),
]

LIMITATIONS: list[str] = [
    "VisoNarc is an experimental academic prototype. Its measurements are not medical, forensic or legal evidence.",
    "Facial appearance, eye redness, pupil-region size, voice and movement cannot establish drug use or identify "
    "any substance. Many ordinary factors (fatigue, illness, allergies, lighting, camera, microphone, emotion, "
    "speaking style, disability) change the same measurements.",
    "No model has been trained or evaluated, so no score, probability, confidence or classification is produced.",
    "No population reference ranges are applied; values are shown as measured, without labelling them normal or abnormal.",
    "Face pixel statistics and expression coefficients are computed in the browser; the server validates their "
    "ranges but cannot verify them.",
    "Webcam images rarely resolve the pupil reliably; pupil-region ratios are approximate and often unavailable.",
    "Quality gates (brightness, sharpness, signal-to-noise, tracking coverage) are engineering thresholds chosen for "
    "this prototype and have not been validated.",
]


MODALITY_ORDER = ("face", "motion", "voice")

# Deterministic feature order for feature-integration records: modality order, then catalogue order.
# Only scalar "summary" features are integrated. Changing this list requires a new INTEGRATION_VERSION.
INTEGRATION_FEATURES: tuple[tuple[str, str], ...] = tuple(
    (spec.modality, spec.key)
    for modality in MODALITY_ORDER
    for spec in FEATURES
    if spec.modality == modality and spec.summary
)
INTEGRATION_VERSION = "integration/1.0.0+latest-reliable-per-modality"
# Schema label of a combined record whose inputs were captured under different feature schemas.
MIXED_SCHEMAS = "mixed"


def catalogue() -> list[dict]:
    return [asdict(f) for f in FEATURES]


def spec(modality: str, key: str) -> FeatureSpec | None:
    return next((f for f in FEATURES if f.modality == modality and f.key == key), None)
