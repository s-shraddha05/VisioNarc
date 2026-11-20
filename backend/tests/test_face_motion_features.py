import numpy as np
import pytest

from app.analysis.common import FeatureError
from app.analysis.face import extract_face_features
from app.analysis.motion import extract_motion_features
from tests.analysis_fixtures import (
    FACE_H,
    FACE_W,
    GOOD_PIXEL_STATS,
    POSE_H,
    POSE_W,
    face_landmarks,
    pose_sequence,
)


def face(**kwargs):
    stats = {**GOOD_PIXEL_STATS, **kwargs.pop("stats", {})}
    return extract_face_features(face_landmarks(**kwargs), FACE_W, FACE_H, stats, {"jawOpen": 0.1, "bogusKey": 0.9})


def test_face_geometry_symmetric_open_eyes():
    r = face()
    f = r.features
    assert f["ear_image_left"] == pytest.approx(0.25, abs=1e-3)
    assert f["ear_image_right"] == pytest.approx(0.25, abs=1e-3)
    assert f["ear_asymmetry"] == pytest.approx(0, abs=1e-3)
    assert f["symmetry_index"] == pytest.approx(1.0, abs=1e-3)
    assert f["iris_diameter_px_image_left"] == pytest.approx(0.05 * FACE_W, abs=0.1)
    assert f["iris_to_eye_width_ratio"] == pytest.approx(0.05 / 0.08, abs=1e-3)
    assert f["pupil_to_iris_ratio_image_left"] == 0.35  # iris 32 px >= 30 px: browser value kept
    assert r.warnings == []
    assert f["frontal_offset"] == pytest.approx(0, abs=1e-6)
    assert f["mouth_aspect_ratio"] == pytest.approx(0.02 / 0.12, abs=1e-3)
    # Browser values pass through; unknown expression keys are dropped.
    assert f["brightness_mean"] == 120.0
    assert f["expression_scores"] == {"jawOpen": 0.1}
    assert r.is_reliable and r.quality_score == 1.0


def test_face_asymmetry_lowers_index():
    # Two of ten mirrored pairs are offset by 32.0 px and 36.2 px; inter-ocular distance is 153.6 px:
    # 1 - (32.0 + 36.2) / 10 / 153.6 = 0.9556
    assert face(asymmetric=True).features["symmetry_index"] == pytest.approx(0.9556, abs=5e-4)


def test_face_quality_gates():
    closed = face(closed_eyes=True)
    assert closed.features["ear_mean"] == pytest.approx(0, abs=1e-6)
    assert not closed.is_reliable
    assert any("Eyes appear closed" in w for w in closed.warnings)

    dark = face(stats={"brightness_mean": 20.0, "sharpness_laplacian_var": 5.0})
    assert dark.quality_score == pytest.approx(0.6)
    assert len(dark.warnings) == 2  # lighting + sharpness

    no_pupil = face(stats={"pupil_to_iris_ratio_image_left": None, "pupil_to_iris_ratio_image_right": None})
    assert any("Pupil-region size was not measured" in w for w in no_pupil.warnings)


def test_server_withholds_unsupported_eye_values():
    # Closed eyes: browser redness/pupil values are not supported by the geometry -> withheld.
    closed = face(closed_eyes=True).features
    assert closed["eye_redness_image_left"] is None and closed["pupil_to_iris_ratio_image_left"] is None

    # Small iris (19 px): pupil withheld even though the browser sent a value; redness kept.
    lm = face_landmarks()
    for centre, ring in ((468, (469, 470, 471, 472)), (473, (474, 475, 476, 477))):
        cx, cy = lm[centre, :2]
        for i, (dx, dy) in zip(ring, ((0.015, 0), (0, -0.015), (-0.015, 0), (0, 0.015))):
            lm[i, :2] = (cx + dx, cy + dy)
    small = extract_face_features(lm, FACE_W, FACE_H, dict(GOOD_PIXEL_STATS), {})
    assert small.features["iris_diameter_px_image_left"] == pytest.approx(19.2, abs=0.1)
    assert small.features["pupil_to_iris_ratio_image_left"] is None
    assert small.features["eye_redness_image_left"] == 0.40
    assert any("iris is 19 px wide" in w for w in small.warnings)

    # Tiny face in a large image: eye width < 20 px -> all eye-region pixel values withheld.
    tiny = extract_face_features(face_landmarks(), 200, 200, dict(GOOD_PIXEL_STATS), {})
    assert tiny.features["eye_redness_image_right"] is None
    assert any("too small" in w for w in tiny.warnings)


def test_face_extraction_is_deterministic():
    a = face().features
    b = face().features
    assert a == b


def test_face_rejects_bad_landmarks():
    with pytest.raises(FeatureError):
        extract_face_features(np.zeros((100, 3)), FACE_W, FACE_H, GOOD_PIXEL_STATS, {})
    lm = face_landmarks()
    lm[5, 0] = np.nan
    with pytest.raises(FeatureError):
        extract_face_features(lm, FACE_W, FACE_H, GOOD_PIXEL_STATS, {})


def motion(**kwargs):
    t, lm = pose_sequence(**kwargs)
    return extract_motion_features(t, lm, POSE_W, POSE_H)


@pytest.mark.parametrize("freq", [0.5, 2.0, 4.0])
def test_motion_dominant_frequency(freq):
    r = motion(nose_freq_hz=freq)
    assert r.features["dominant_frequency_hz"] == pytest.approx(freq, abs=0.11)
    assert r.features["dominant_power_fraction"] > 0.5


def test_motion_static_vs_moving():
    still = motion(nose_freq_hz=None).features
    moving = motion(nose_freq_hz=2.0).features
    assert still["mean_speed_bw_s"] < 0.05
    assert moving["mean_speed_bw_s"] > 5 * still["mean_speed_bw_s"]
    # Nose amplitude 0.02 * 640 px = 0.1 shoulder widths; mean |speed| of a sine = 4 * A * f.
    assert moving["head_speed_bw_s"] == pytest.approx(4 * 0.1 * 2.0, rel=0.1)


def test_motion_posture():
    r = motion(tilt_deg=10.0)
    assert r.features["shoulder_tilt_deg_mean"] == pytest.approx(10.0, abs=0.2)
    assert r.features["shoulder_tilt_deg_std"] == pytest.approx(0, abs=1e-6)
    assert r.features["trunk_lean_deg_mean"] == pytest.approx(0, abs=1e-6)
    assert r.is_reliable and r.features["tracked_fraction"] == 1.0

    no_hips = motion(hips=False)
    assert no_hips.features["trunk_lean_deg_mean"] is None
    assert any("Hips" in w for w in no_hips.warnings)


def test_motion_patchy_tracking_not_reliable():
    r = motion(missing_fraction=0.6)
    assert r.features["tracked_fraction"] < 0.7
    assert not r.is_reliable
    assert any("tracked in only" in w for w in r.warnings)


def test_motion_rejects_short_and_untracked():
    with pytest.raises(FeatureError, match="too short"):
        motion(seconds=3)
    t, lm = pose_sequence()
    lm[:] = np.nan
    with pytest.raises(FeatureError, match="fewer than 10 frames"):
        extract_motion_features(t, lm, POSE_W, POSE_H)
