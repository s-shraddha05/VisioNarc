"""Facial measurements from MediaPipe Face Landmarker output (478 landmarks) of a single image.

Landmark geometry is computed here on the server. Pixel statistics and expression coefficients
are computed in the browser and are only range-checked (by the request schema) and stored.
Landmark indices follow the MediaPipe Face Mesh topology (Kartynnik et al., 2019).
"""

from typing import Any

import numpy as np

from app.analysis.common import ExtractionResult, FeatureError, clamp01, clean

# Server extractor version + the browser pipeline it expects (frontend pins tasks-vision 1.1.0).
EXTRACTOR_VERSION = "face/1.1.0+mp-tasks-vision-1.1.0+face_landmarker-f16v1"

N_LANDMARKS = 478
# Six-point eye contours ordered p1..p6 as in Soukupová & Čech (2016): corner, top, top, corner, bottom, bottom.
EYES = ([33, 160, 158, 133, 153, 144], [362, 385, 387, 263, 373, 380])
IRISES = ([468, 469, 470, 471, 472], [473, 474, 475, 476, 477])  # centre + 4 ring points
SYMMETRIC_PAIRS = [
    (33, 263), (133, 362), (61, 291), (234, 454), (70, 300),
    (105, 334), (98, 327), (172, 397), (159, 386), (145, 374),
]
MIDLINE = (10, 152)  # forehead, chin
NOSE_TIP, CHEEK_A, CHEEK_B = 1, 234, 454
LIP_TOP, LIP_BOTTOM, MOUTH_A, MOUTH_B = 13, 14, 61, 291

EXPRESSION_KEYS = (
    "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight",
    "browDownLeft", "browDownRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight",
)

# Engineering quality gates for this prototype (not validated reference values).
MIN_FACE_WIDTH = 0.20
MAX_FRONTAL_OFFSET = 0.15
BRIGHTNESS_RANGE = (50.0, 210.0)
MIN_SHARPNESS = 20.0
MIN_EAR_FOR_EYE_MEASURES = 0.12
# Below these sizes the browser's eye-region pixel values cannot be supported, so the server
# withholds them (stores None) instead of trusting the client.
MIN_IRIS_PX_FOR_PUPIL = 30.0
MIN_EYE_WIDTH_PX = 20.0
EYE_PIXEL_KEYS = ("eye_redness_image_left", "eye_redness_image_right")
PUPIL_KEYS = ("pupil_to_iris_ratio_image_left", "pupil_to_iris_ratio_image_right")


def _ear(p: np.ndarray) -> float:
    horizontal = np.linalg.norm(p[0] - p[3])
    if horizontal < 1e-6:
        return float("nan")
    return float((np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])) / (2 * horizontal))


def _symmetry_index(pts: np.ndarray) -> float:
    a, b = pts[MIDLINE[0]], pts[MIDLINE[1]]
    axis = b - a
    length = np.linalg.norm(axis)
    interocular = np.linalg.norm(pts[33] - pts[263])
    if length < 1e-6 or interocular < 1e-6:
        return float("nan")
    u = axis / length
    n = np.array([-u[1], u[0]])
    offsets = []
    for i, j in SYMMETRIC_PAIRS:
        di, dj = np.dot(pts[i] - a, n), np.dot(pts[j] - a, n)
        si, sj = np.dot(pts[i] - a, u), np.dot(pts[j] - a, u)
        # Distance between j and the mirror image of i across the midline.
        offsets.append(np.hypot(dj + di, sj - si))
    return clamp01(1.0 - float(np.mean(offsets)) / interocular)


def extract_face_features(
    landmarks: np.ndarray,
    width: int,
    height: int,
    pixel_stats: dict[str, float | None],
    expressions: dict[str, float],
) -> ExtractionResult:
    if landmarks.shape != (N_LANDMARKS, 3) or not np.all(np.isfinite(landmarks)):
        raise FeatureError(f"Expected {N_LANDMARKS} finite face landmarks with x, y, z.")
    pts = landmarks[:, :2] * np.array([width, height], dtype=float)

    eyes = [pts[idx] for idx in EYES]
    eye_centres = [e.mean(axis=0) for e in eyes]
    # Name eyes by image side so the result does not depend on mirroring conventions.
    order = np.argsort([c[0] for c in eye_centres])
    left_eye, right_eye = eyes[order[0]], eyes[order[1]]
    ear_left, ear_right = _ear(left_eye), _ear(right_eye)
    ear_mean = float(np.nanmean([ear_left, ear_right]))

    iris_d = {}
    for ring in IRISES:
        p = pts[ring]
        diameter = float(np.mean([np.linalg.norm(p[1] - p[3]), np.linalg.norm(p[2] - p[4])]))
        side = "left" if np.linalg.norm(p[0] - eye_centres[order[0]]) < np.linalg.norm(p[0] - eye_centres[order[1]]) else "right"
        iris_d[side] = diameter
    eye_widths = [np.linalg.norm(left_eye[0] - left_eye[3]), np.linalg.norm(right_eye[0] - right_eye[3])]
    iris_ratio = (
        np.mean(list(iris_d.values())) / np.mean(eye_widths) if len(iris_d) == 2 and np.mean(eye_widths) > 0 else None
    )

    xs = pts[:, 0]
    face_width_fraction = (xs.max() - xs.min()) / width
    cheek_span = abs(pts[CHEEK_B, 0] - pts[CHEEK_A, 0])
    frontal_offset = (
        (pts[NOSE_TIP, 0] - (pts[CHEEK_A, 0] + pts[CHEEK_B, 0]) / 2) / cheek_span if cheek_span > 1e-6 else float("nan")
    )
    mouth_width = np.linalg.norm(pts[MOUTH_A] - pts[MOUTH_B])
    mar = np.linalg.norm(pts[LIP_TOP] - pts[LIP_BOTTOM]) / mouth_width if mouth_width > 1e-6 else float("nan")

    features: dict[str, Any] = {
        "face_width_fraction": clean(face_width_fraction, 3),
        "frontal_offset": clean(frontal_offset, 3),
        "ear_image_left": clean(ear_left, 4),
        "ear_image_right": clean(ear_right, 4),
        "ear_mean": clean(ear_mean, 4),
        "ear_asymmetry": clean(abs(ear_left - ear_right) / ear_mean, 3) if ear_mean > 1e-6 else None,
        "mouth_aspect_ratio": clean(mar, 4),
        "symmetry_index": clean(_symmetry_index(pts), 4),
        "iris_diameter_px_image_left": clean(iris_d.get("left"), 1),
        "iris_diameter_px_image_right": clean(iris_d.get("right"), 1),
        "iris_to_eye_width_ratio": clean(iris_ratio, 4),
    }
    for key, value in pixel_stats.items():
        features[key] = clean(value, 4)
    features["expression_scores"] = {k: clean(v, 3) for k, v in expressions.items() if k in EXPRESSION_KEYS}

    warnings: list[str] = []
    # Server-side support checks for browser-computed eye-region values (geometry is verifiable here).
    mean_eye_width = float(np.mean(eye_widths))
    mean_iris = float(np.mean(list(iris_d.values()))) if iris_d else 0.0
    if ear_mean < MIN_EAR_FOR_EYE_MEASURES or mean_eye_width < MIN_EYE_WIDTH_PX:
        withheld = [k for k in EYE_PIXEL_KEYS + PUPIL_KEYS if features.get(k) is not None]
        for k in EYE_PIXEL_KEYS + PUPIL_KEYS:
            features[k] = None
        if withheld:
            warnings.append(
                "Eye-region colour and pupil-region values were withheld: the eyes are nearly closed or too small "
                f"in the image (eye width {mean_eye_width:.0f} px)."
            )
    elif mean_iris < MIN_IRIS_PX_FOR_PUPIL and any(features.get(k) is not None for k in PUPIL_KEYS):
        for k in PUPIL_KEYS:
            features[k] = None
        warnings.append(
            f"Pupil-region values were withheld: the iris is {mean_iris:.0f} px wide "
            f"(at least {MIN_IRIS_PX_FOR_PUPIL:.0f} px needed)."
        )
    gates = {
        "face size": face_width_fraction >= MIN_FACE_WIDTH,
        "frontal pose": abs(frontal_offset) <= MAX_FRONTAL_OFFSET if np.isfinite(frontal_offset) else False,
        "lighting": BRIGHTNESS_RANGE[0] <= (pixel_stats.get("brightness_mean") or 0) <= BRIGHTNESS_RANGE[1],
        "sharpness": (pixel_stats.get("sharpness_laplacian_var") or 0) >= MIN_SHARPNESS,
        "open eyes": ear_mean >= MIN_EAR_FOR_EYE_MEASURES,
    }
    messages = {
        "face size": "The face is small in the frame; move closer to the camera.",
        "frontal pose": "The head is turned; face the camera directly.",
        "lighting": "Lighting is too dark or too bright for reliable pixel measurements.",
        "sharpness": "The image is blurry; hold still and focus the camera.",
        "open eyes": "Eyes appear closed or nearly closed; eye measurements are unreliable.",
    }
    warnings.extend(messages[name] for name, ok in gates.items() if not ok)
    if features.get("pupil_to_iris_ratio_image_left") is None and features.get("pupil_to_iris_ratio_image_right") is None:
        warnings.append("Pupil-region size was not measured (iris too small in the image or region unclear).")
    quality = sum(gates.values()) / len(gates)
    return ExtractionResult(features=features, warnings=warnings, quality_score=round(quality, 3), is_reliable=all(gates.values()))
