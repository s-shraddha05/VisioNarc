"""Synthetic landmark/audio builders for tests. Geometry only — not real or training data."""

import io
import math
import wave

import numpy as np

FACE_W = FACE_H = 640


def face_landmarks(asymmetric: bool = False, closed_eyes: bool = False) -> np.ndarray:
    lm = np.zeros((478, 3))
    # Background points spread inside a plausible face box.
    lm[:, 0] = np.linspace(0.32, 0.68, 478)
    lm[:, 1] = np.linspace(0.30, 0.78, 478)
    points = {
        # eye A: p1..p6 = 33, 160, 158, 133, 153, 144
        33: (0.38, 0.42), 160: (0.40, 0.41), 158: (0.44, 0.41), 133: (0.46, 0.42), 153: (0.44, 0.43), 144: (0.40, 0.43),
        # eye B: 362, 385, 387, 263, 373, 380 (mirror of eye A)
        362: (0.54, 0.42), 385: (0.56, 0.41), 387: (0.60, 0.41), 263: (0.62, 0.42), 373: (0.60, 0.43), 380: (0.56, 0.43),
        468: (0.42, 0.42), 469: (0.445, 0.42), 470: (0.42, 0.395), 471: (0.395, 0.42), 472: (0.42, 0.445),
        473: (0.58, 0.42), 474: (0.605, 0.42), 475: (0.58, 0.395), 476: (0.555, 0.42), 477: (0.58, 0.445),
        10: (0.50, 0.25), 152: (0.50, 0.80), 1: (0.50, 0.55), 234: (0.30, 0.55), 454: (0.70, 0.55),
        61: (0.44, 0.68), 291: (0.56, 0.68), 13: (0.50, 0.67), 14: (0.50, 0.69),
        70: (0.38, 0.36), 300: (0.62, 0.36), 105: (0.42, 0.35), 334: (0.58, 0.35),
        98: (0.47, 0.58), 327: (0.53, 0.58), 172: (0.34, 0.70), 397: (0.66, 0.70),
        159: (0.42, 0.41), 386: (0.58, 0.41), 145: (0.42, 0.43), 374: (0.58, 0.43),
    }
    for i, (x, y) in points.items():
        lm[i, :2] = (x, y)
    if asymmetric:
        lm[291, :2] = (0.60, 0.71)
        lm[397, :2] = (0.70, 0.74)
    if closed_eyes:
        for i in (160, 158, 153, 144, 385, 387, 373, 380):
            lm[i, 1] = 0.42
    return lm


GOOD_PIXEL_STATS = {
    "brightness_mean": 120.0,
    "contrast_std": 40.0,
    "sharpness_laplacian_var": 80.0,
    "eye_redness_image_left": 0.40,
    "eye_redness_image_right": 0.41,
    "pupil_to_iris_ratio_image_left": 0.35,
    "pupil_to_iris_ratio_image_right": 0.36,
}

POSE_W, POSE_H = 640, 480


def pose_sequence(
    seconds: float = 10.0,
    fps: float = 15.0,
    nose_freq_hz: float | None = 2.0,
    tilt_deg: float = 0.0,
    missing_fraction: float = 0.0,
    hips: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    n = int(seconds * fps) + 1
    t_ms = np.arange(n) * 1000.0 / fps
    lm = np.zeros((n, 33, 4))
    lm[:, :, :2] = 0.5
    lm[:, :, 3] = 0.9
    half_dy = math.tan(math.radians(tilt_deg)) * (0.2 * POSE_W) / 2 / POSE_H
    base = {0: (0.5, 0.3), 11: (0.6, 0.45 - half_dy), 12: (0.4, 0.45 + half_dy), 13: (0.65, 0.6), 14: (0.35, 0.6),
            15: (0.66, 0.75), 16: (0.34, 0.75), 23: (0.57, 0.85), 24: (0.43, 0.85)}
    for i, (x, y) in base.items():
        lm[:, i, 0], lm[:, i, 1] = x, y
    if not hips:
        lm[:, [23, 24], 3] = 0.1
    if nose_freq_hz:
        lm[:, 0, 0] += 0.02 * np.sin(2 * np.pi * nose_freq_hz * t_ms / 1000.0)
    else:
        lm[:, 0, 0] += 0.0005 * np.random.default_rng(1).standard_normal(n)
    if missing_fraction:
        drop = np.random.default_rng(2).random(n) < missing_fraction
        lm[drop] = np.nan
    return t_ms, lm


def pose_payload(**kwargs) -> dict:
    t_ms, lm = pose_sequence(**kwargs)
    frames = []
    for t, frame in zip(t_ms, lm):
        frames.append({"t_ms": float(t), "landmarks": None if np.isnan(frame[0, 0]) else frame.round(5).tolist()})
    return {"source": "webcam", "video_width": POSE_W, "video_height": POSE_H, "frames": frames}


def face_payload(**kwargs) -> dict:
    return {
        "source": "upload",
        "image_width": FACE_W,
        "image_height": FACE_H,
        "landmarks": face_landmarks(**kwargs).round(5).tolist(),
        "pixel_stats": dict(GOOD_PIXEL_STATS),  # copy: tests mutate payloads
        "expressions": {"eyeBlinkLeft": 0.05, "jawOpen": 0.01},
    }


def voice_wav(seconds_tone: float = 1.5, freq: float = 200.0) -> bytes:
    sr = 16000
    rng = np.random.default_rng(0)

    def quiet(s):
        return 0.002 * rng.standard_normal(int(sr * s))

    def tone(s):
        t = np.arange(int(sr * s)) / sr
        return 0.3 * np.sin(2 * np.pi * freq * t) + quiet(s)

    x = np.concatenate([quiet(0.5), tone(seconds_tone), quiet(0.6), tone(seconds_tone), quiet(0.5)])
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()
