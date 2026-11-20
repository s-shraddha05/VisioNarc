"""Upper-body movement measurements from MediaPipe Pose Landmarker output (33 landmarks per frame).

Landmark indices follow the BlazePose topology (Bazarevsky et al., 2020). All distances are
normalised by the median shoulder width so results do not depend on camera distance.
"""

from typing import Any

import numpy as np

from app.analysis.common import ExtractionResult, FeatureError, clean

# 1.1.0: browser now sends the actual decoded frame time (not the requested seek time).
EXTRACTOR_VERSION = "motion/1.1.0+mp-tasks-vision-1.1.0+pose_lite-f16v1@15fps"

N_POSE = 33
NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP = 0, 11, 12, 13, 14, 15, 16, 23, 24
UPPER_BODY = [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST]
MIN_SECONDS, MAX_SECONDS = 5.0, 65.0
VISIBLE = 0.5
RESAMPLE_HZ = 15.0
BAND_HZ = (0.25, 7.5)

# Engineering quality gates for this prototype (not validated reference values).
MIN_TRACKED_FRACTION = 0.7
MIN_TRACKED_FRAMES = 50


def _fold_angle(deg: np.ndarray) -> np.ndarray:
    """Map line angles to (-90, 90] so a line's direction does not matter."""
    deg = np.where(deg > 90, deg - 180, deg)
    return np.where(deg <= -90, deg + 180, deg)


def extract_motion_features(times_ms: np.ndarray, landmarks: np.ndarray, width: int, height: int) -> ExtractionResult:
    """times_ms: (n,), strictly increasing. landmarks: (n, 33, 4) [x, y, z, visibility], NaN where no pose."""
    n = len(times_ms)
    t = (times_ms - times_ms[0]) / 1000.0
    duration = float(t[-1]) if n else 0.0
    if duration < MIN_SECONDS:
        raise FeatureError(f"Clip is too short ({duration:.1f} s; at least {MIN_SECONDS:.0f} s needed).")
    if duration > MAX_SECONDS:
        raise FeatureError(f"Clip is too long ({duration:.0f} s; at most 60 s).")

    present = ~np.isnan(landmarks[:, 0, 0])
    vis = np.nan_to_num(landmarks[:, :, 3], nan=0.0)
    tracked = present & (vis[:, [NOSE, L_SHOULDER, R_SHOULDER]].min(axis=1) >= VISIBLE)
    n_tracked = int(tracked.sum())
    if n_tracked < 10:
        raise FeatureError("A body pose (head and both shoulders) was detected in fewer than 10 frames.")

    px = landmarks[:, :, :2] * np.array([width, height], dtype=float)
    shoulder_vec = px[:, L_SHOULDER] - px[:, R_SHOULDER]
    scale = float(np.median(np.linalg.norm(shoulder_vec[tracked], axis=1)))
    if scale < 10:
        raise FeatureError("The person is too small in the frame to measure movement.")

    warnings: list[str] = []
    # Speeds between consecutive tracked frames, per keypoint, in shoulder widths per second.
    pair = tracked[:-1] & tracked[1:]
    dt = np.diff(t)
    pair &= (dt > 0) & (dt <= 0.5)
    idx = np.flatnonzero(pair)
    disp = np.linalg.norm(px[idx + 1][:, UPPER_BODY] - px[idx][:, UPPER_BODY], axis=2) / scale / dt[idx, None]
    ok = (vis[idx][:, UPPER_BODY] >= VISIBLE) & (vis[idx + 1][:, UPPER_BODY] >= VISIBLE)
    disp = np.where(ok, disp, np.nan)
    with np.errstate(invalid="ignore"):
        frame_speed = np.nanmean(disp, axis=1)
    frame_speed = frame_speed[np.isfinite(frame_speed)]
    head_speed = disp[:, 0][np.isfinite(disp[:, 0])]
    wrist_speed = disp[:, [5, 6]][np.isfinite(disp[:, [5, 6]])]

    features: dict[str, Any] = {
        "duration_s": clean(duration, 2),
        "tracked_fraction": clean(n_tracked / n, 3),
        "mean_speed_bw_s": None,
        "speed_std_bw_s": None,
        "speed_p95_bw_s": None,
        "movement_variability_cv": None,
        "head_speed_bw_s": clean(head_speed.mean(), 4) if head_speed.size else None,
        "wrist_speed_bw_s": clean(wrist_speed.mean(), 4) if wrist_speed.size else None,
    }
    if frame_speed.size >= 5:
        mean = float(frame_speed.mean())
        features.update(
            mean_speed_bw_s=clean(mean, 4),
            speed_std_bw_s=clean(frame_speed.std(), 4),
            speed_p95_bw_s=clean(np.percentile(frame_speed, 95), 4),
            movement_variability_cv=clean(frame_speed.std() / mean, 3) if mean > 1e-6 else None,
        )
    else:
        warnings.append("Too few consecutive tracked frames to measure speed.")

    # Dominant movement frequency from detrended head/wrist positions on a uniform 15 Hz grid.
    features.update(dominant_frequency_hz=None, dominant_power_fraction=None)
    if n_tracked / n >= 0.5 and duration >= 4 / BAND_HZ[0] / 2:
        grid = np.arange(0, duration, 1 / RESAMPLE_HZ)
        signals = [px[:, NOSE, 0], px[:, NOSE, 1]]
        for wrist in (L_WRIST, R_WRIST):
            if np.mean(vis[tracked, wrist] >= VISIBLE) >= 0.5:
                signals.append(px[:, wrist, 1])
        power = None
        for s in signals:
            keep = tracked & np.isfinite(s)
            y = np.interp(grid, t[keep], s[keep] / scale)
            y = y - np.polyval(np.polyfit(grid, y, 1), grid)
            p = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
            power = p if power is None else power + p
        freqs = np.fft.rfftfreq(len(grid), 1 / RESAMPLE_HZ)
        band = (freqs >= BAND_HZ[0]) & (freqs <= BAND_HZ[1])
        if power is not None and band.any() and power[band].sum() > 0:
            k = np.flatnonzero(band)[np.argmax(power[band])]
            features["dominant_frequency_hz"] = clean(freqs[k], 3)
            features["dominant_power_fraction"] = clean(power[max(k - 1, 0) : k + 2].sum() / power[band].sum(), 3)
    else:
        warnings.append("Pose tracking was too patchy to estimate a movement frequency.")

    # Posture.
    tr = np.flatnonzero(tracked)
    tilt = _fold_angle(np.degrees(np.arctan2(shoulder_vec[tr, 1], shoulder_vec[tr, 0])))
    mid_sh = (px[tr, L_SHOULDER] + px[tr, R_SHOULDER]) / 2
    head_offset = (px[tr, NOSE, 0] - mid_sh[:, 0]) / scale
    features.update(
        shoulder_tilt_deg_mean=clean(np.abs(tilt).mean(), 2),
        shoulder_tilt_deg_std=clean(tilt.std(), 2),
        head_offset_std_bw=clean(head_offset.std(), 4),
        trunk_lean_deg_mean=None,
        trunk_lean_deg_std=None,
    )
    hips = vis[tr][:, [L_HIP, R_HIP]].min(axis=1) >= VISIBLE
    if hips.mean() >= 0.5:
        hp = tr[hips]
        mid_hip = (px[hp, L_HIP] + px[hp, R_HIP]) / 2
        sh = (px[hp, L_SHOULDER] + px[hp, R_SHOULDER]) / 2
        lean = np.degrees(np.arctan2(sh[:, 0] - mid_hip[:, 0], mid_hip[:, 1] - sh[:, 1]))
        features.update(trunk_lean_deg_mean=clean(np.abs(lean).mean(), 2), trunk_lean_deg_std=clean(lean.std(), 2))
    else:
        warnings.append("Hips were not visible in most frames; trunk lean was not measured.")

    tracked_fraction = n_tracked / n
    if tracked_fraction < MIN_TRACKED_FRACTION:
        warnings.append(f"Pose was tracked in only {tracked_fraction:.0%} of frames; keep head and shoulders in view.")
    quality = tracked_fraction * float(vis[tracked][:, [NOSE, L_SHOULDER, R_SHOULDER]].mean())
    reliable = tracked_fraction >= MIN_TRACKED_FRACTION and n_tracked >= MIN_TRACKED_FRAMES and duration >= MIN_SECONDS
    return ExtractionResult(features=features, warnings=warnings, quality_score=round(quality, 3), is_reliable=reliable)
