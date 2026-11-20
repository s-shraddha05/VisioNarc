import pytest
from sqlalchemy import select

from app.models import AuditLog, VoiceMeasurement
from tests.analysis_fixtures import face_payload, pose_payload, voice_wav

SESSIONS = "/api/v1/sessions"


def new_session(client, headers, face=True, motion=True, voice=True):
    body = {
        "subject_label": "Participant",
        "consent": {"consent_given": True, "consented_by_label": "P", "allow_face": face,
                    "allow_motion": motion, "allow_voice": voice},
    }
    response = client.post(SESSIONS, json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def post_voice(client, headers, sid, data=None, consent=True, ctype="audio/wav"):
    return client.post(
        f"{SESSIONS}/{sid}/analysis/voice",
        params={"source": "microphone", "upload_consent": str(consent).lower()},
        content=voice_wav() if data is None else data,
        headers={**headers, "Content-Type": ctype},
    )


def test_analysis_endpoints_require_auth(client):
    assert client.post(f"{SESSIONS}/1/analysis/face", json=face_payload()).status_code == 401
    assert client.post(f"{SESSIONS}/1/analysis/motion", json=pose_payload()).status_code == 401
    assert client.post(f"{SESSIONS}/1/analysis/voice?source=microphone&upload_consent=true", content=b"x").status_code == 401
    assert client.get(f"{SESSIONS}/1/multimodal-summary").status_code == 401
    assert client.post(f"{SESSIONS}/1/complete").status_code == 401
    assert client.get("/api/v1/analysis/feature-schema").status_code == 401


def test_face_measurement_persisted_and_audited(client, auth_headers, db):
    sid = new_session(client, auth_headers)
    response = client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_reliable"] is True
    assert body["features"]["symmetry_index"] == pytest.approx(1.0, abs=1e-3)
    assert body["feature_schema_version"] == "1.1"
    assert body["extractor_version"].startswith("face/1.1.0+mp-tasks-vision-1.1.0")

    detail = client.get(f"{SESSIONS}/{sid}", headers=auth_headers).json()
    assert detail["status"] == "in_progress"
    assert detail["counts"]["face"] == 1

    log = db.scalars(select(AuditLog).where(AuditLog.action == "analysis.face_measured")).one()
    # Audit records that a measurement happened, never its values.
    assert set(log.details) == {"measurement_id", "is_reliable"}


def test_motion_measurement(client, auth_headers):
    sid = new_session(client, auth_headers)
    response = client.post(f"{SESSIONS}/{sid}/analysis/motion", json=pose_payload(), headers=auth_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["features"]["dominant_frequency_hz"] == pytest.approx(2.0, abs=0.11)
    assert body["frames_processed"] == 151 and body["frames_with_pose"] == 151
    assert body["extractor_version"].startswith("motion/1.1.0")


def test_voice_measurement_in_memory(client, auth_headers, db):
    sid = new_session(client, auth_headers)
    response = post_voice(client, auth_headers, sid)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["features"]["f0_median_hz"] == pytest.approx(200, rel=0.02)
    assert body["sample_rate"] == 16000 and body["snr_db"] > 20
    assert body["extractor_version"].startswith("voice/1.0.0")
    row = db.scalars(select(VoiceMeasurement)).one()
    # Only numeric features are stored: no bytes/arrays of raw audio.
    assert all(not isinstance(v, (bytes, bytearray)) for v in row.features.values())
    assert max(len(v) if isinstance(v, list) else 1 for v in row.features.values()) == 13  # MFCC means only


def test_voice_requires_explicit_upload_consent_and_wav(client, auth_headers):
    sid = new_session(client, auth_headers)
    assert post_voice(client, auth_headers, sid, consent=False).status_code == 400
    assert post_voice(client, auth_headers, sid, ctype="audio/mpeg").status_code == 415
    assert post_voice(client, auth_headers, sid, data=b"RIFF" + b"\0" * (4 * 1024 * 1024 + 10)).status_code == 413
    bad = post_voice(client, auth_headers, sid, data=b"not a wav" * 10)
    assert bad.status_code == 422 and "WAV" in bad.json()["detail"]


def test_consent_is_enforced_per_modality(client, auth_headers):
    sid = new_session(client, auth_headers, face=True, motion=False, voice=False)
    assert client.post(f"{SESSIONS}/{sid}/analysis/motion", json=pose_payload(), headers=auth_headers).status_code == 403
    assert post_voice(client, auth_headers, sid).status_code == 403
    assert client.post(f"{SESSIONS}/999/analysis/face", json=face_payload(), headers=auth_headers).status_code == 404

    client.post(f"{SESSIONS}/{sid}/withdraw-consent", headers=auth_headers)
    withdrawn = client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    assert withdrawn.status_code == 409


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(landmarks=p["landmarks"][:100]),
        lambda p: p["landmarks"][0].__setitem__(0, 5.0),
        lambda p: p["pixel_stats"].update(brightness_mean=999),
        lambda p: p["pixel_stats"].update(eye_redness_image_left=1.5),
        lambda p: p["expressions"].update(jawOpen=2.0),
        lambda p: p.update(extra_field=1),
        lambda p: p.update(image_width=100),
    ],
    ids=["too-few-landmarks", "landmark-out-of-frame", "brightness-range", "redness-range",
         "expression-range", "unknown-field", "tiny-image"],
)
def test_face_submission_validation(client, auth_headers, mutate):
    sid = new_session(client, auth_headers)
    payload = face_payload()
    mutate(payload)
    assert client.post(f"{SESSIONS}/{sid}/analysis/face", json=payload, headers=auth_headers).status_code == 422


def test_motion_submission_validation(client, auth_headers):
    sid = new_session(client, auth_headers)
    payload = pose_payload()
    payload["frames"][5]["t_ms"] = payload["frames"][4]["t_ms"]
    assert client.post(f"{SESSIONS}/{sid}/analysis/motion", json=payload, headers=auth_headers).status_code == 422
    short = pose_payload(seconds=3)
    response = client.post(f"{SESSIONS}/{sid}/analysis/motion", json=short, headers=auth_headers)
    assert response.status_code == 422 and "too short" in response.json()["detail"]


def test_multimodal_summary_has_no_score(client, auth_headers):
    sid = new_session(client, auth_headers, face=True, motion=False, voice=True)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    summary = client.get(f"{SESSIONS}/{sid}/multimodal-summary", headers=auth_headers).json()

    assert summary["available_modalities"] == ["face"]
    assert summary["missing_modalities"] == ["motion", "voice"]
    by = {m["modality"]: m for m in summary["modalities"]}
    assert by["face"]["status"] == "available" and by["face"]["key_features"]
    assert by["motion"]["status"] == "not_consented"
    assert by["voice"]["status"] == "missing"
    assert summary["limitations"] and summary["method_sources"]
    # No field anywhere in the response carries a score, probability, confidence or label.
    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from keys(item)

    for key in keys(summary):
        assert key == "quality_score" or not any(
            word in key for word in ("score", "probability", "confidence", "class", "indicator", "diagnos")
        ), key
    # Browser-derived values are labelled as such.
    assert {f["provenance"] for f in by["face"]["key_features"]} >= {"server_landmarks", "browser_pixels"}


def test_low_quality_is_reported(client, auth_headers):
    sid = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(closed_eyes=True), headers=auth_headers)
    summary = client.get(f"{SESSIONS}/{sid}/multimodal-summary", headers=auth_headers).json()
    face = next(m for m in summary["modalities"] if m["modality"] == "face")
    assert face["status"] == "low_quality" and face["warnings"]


def test_complete_session(client, auth_headers):
    sid = new_session(client, auth_headers)
    assert client.post(f"{SESSIONS}/{sid}/complete", headers=auth_headers).status_code == 409  # nothing captured
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    done = client.post(f"{SESSIONS}/{sid}/complete", headers=auth_headers)
    assert done.status_code == 200
    assert done.json()["status"] == "completed" and done.json()["completed_at"]
    # A completed session accepts no further captures.
    assert client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers).status_code == 409
    actions = client.get("/api/v1/audit-logs/actions", headers=auth_headers).json()
    assert "session.completed" in actions


def test_feature_schema_catalogue(client, auth_headers):
    body = client.get("/api/v1/analysis/feature-schema", headers=auth_headers).json()
    assert body["version"] == "1.1"
    keys = {(f["modality"], f["key"]) for f in body["features"]}
    assert ("voice", "f0_median_hz") in keys and ("face", "symmetry_index") in keys
    assert all(f["provenance"] in body["provenance"] for f in body["features"])


# ---- Feature integration ---------------------------------------------------------------------

from app.analysis.feature_schema import INTEGRATION_FEATURES  # noqa: E402
from app.models import CombinedResult  # noqa: E402


def capture_all(client, headers, sid):
    assert client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=headers).status_code == 201
    assert client.post(f"{SESSIONS}/{sid}/analysis/motion", json=pose_payload(), headers=headers).status_code == 201
    assert post_voice(client, headers, sid).status_code == 201


def test_integration_requires_auth(client):
    assert client.post(f"{SESSIONS}/1/integrations").status_code == 401
    assert client.get(f"{SESSIONS}/1/integrations").status_code == 401


def test_complete_integration_is_ordered_scoreless_and_reproducible(client, auth_headers):
    sid = new_session(client, auth_headers)
    capture_all(client, auth_headers, sid)
    first = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    assert first.status_code == 201, first.text
    rec = first.json()
    assert rec["mode"] == "feature_integration" and rec["processing_status"] == "complete"
    assert rec["indicator_score"] is None and rec["indicator_level"] is None and rec["confidence"] is None
    assert rec["modalities_used"] == ["face", "motion", "voice"]
    assert [(f["modality"], f["key"]) for f in rec["features"]] == list(INTEGRATION_FEATURES)
    assert [f["index"] for f in rec["features"]] == list(range(len(INTEGRATION_FEATURES)))
    assert rec["extractor_version"].startswith("integration/1.0.0")
    assert {s["modality"] for s in rec["source_measurements"]} == {"face", "motion", "voice"}
    assert all(s["extractor_version"] for s in rec["source_measurements"])

    second = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert second["features"] == rec["features"]  # same inputs -> identical record
    listed = client.get(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert [r["id"] for r in listed] == [second["id"], rec["id"]]  # newest first


def test_partial_integration_keeps_missing_values_missing(client, auth_headers):
    sid = new_session(client, auth_headers, face=True, motion=False, voice=True)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    rec = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert rec["processing_status"] == "partial"
    assert rec["explanation"]["modality_status"] == {"face": "used", "motion": "not_consented", "voice": "missing"}
    voice = [f for f in rec["features"] if f["modality"] == "voice"]
    motion = [f for f in rec["features"] if f["modality"] == "motion"]
    assert voice and all(f["value"] is None and f["status"] == "missing" for f in voice)
    assert motion and all(f["value"] is None and f["status"] == "not_consented" for f in motion)


def test_low_quality_inputs_are_excluded_or_insufficient(client, auth_headers, db):
    sid = new_session(client, auth_headers, face=True, motion=False, voice=False)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(closed_eyes=True), headers=auth_headers)
    response = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    assert response.status_code == 422 and "Insufficient data" in response.json()["detail"]
    assert db.query(CombinedResult).count() == 0  # nothing persisted

    both = new_session(client, auth_headers, face=True, motion=False, voice=True)
    client.post(f"{SESSIONS}/{both}/analysis/face", json=face_payload(closed_eyes=True), headers=auth_headers)
    post_voice(client, auth_headers, both)
    rec = client.post(f"{SESSIONS}/{both}/integrations", headers=auth_headers).json()
    assert rec["explanation"]["modality_status"]["face"] == "excluded_low_quality"
    assert all(f["value"] is None for f in rec["features"] if f["modality"] == "face")


def test_integration_never_mixes_sessions(client, auth_headers):
    a = new_session(client, auth_headers)
    b = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{a}/analysis/face", json=face_payload(), headers=auth_headers)
    voice_b = post_voice(client, auth_headers, b).json()["id"]
    face_a = client.get(f"{SESSIONS}/{a}", headers=auth_headers).json()["facial_measurements"][0]["id"]

    rec_a = client.post(f"{SESSIONS}/{a}/integrations", headers=auth_headers).json()
    assert rec_a["modalities_used"] == ["face"]
    assert [s["measurement_id"] for s in rec_a["source_measurements"]] == [face_a]
    assert {f["measurement_id"] for f in rec_a["features"] if f["measurement_id"]} == {face_a}
    assert client.get(f"{SESSIONS}/{b}/integrations", headers=auth_headers).json() == []
    rec_b = client.post(f"{SESSIONS}/{b}/integrations", headers=auth_headers).json()
    assert [s["measurement_id"] for s in rec_b["source_measurements"]] == [voice_b]


def test_integration_consent_and_lifecycle(client, auth_headers, db):
    assert client.post(f"{SESSIONS}/999/integrations", headers=auth_headers).status_code == 404
    sid = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    client.post(f"{SESSIONS}/{sid}/complete", headers=auth_headers)
    assert client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).status_code == 201  # completed OK

    other = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{other}/analysis/face", json=face_payload(), headers=auth_headers)
    client.post(f"{SESSIONS}/{other}/integrations", headers=auth_headers)
    client.post(f"{SESSIONS}/{other}/withdraw-consent", headers=auth_headers)
    assert client.post(f"{SESSIONS}/{other}/integrations", headers=auth_headers).status_code == 409
    # Withdrawal deleted the record along with the measurements.
    assert client.get(f"{SESSIONS}/{other}/integrations", headers=auth_headers).json() == []
    actions = client.get("/api/v1/audit-logs/actions", headers=auth_headers).json()
    assert "analysis.integration_recorded" in actions


def test_feature_schema_exposes_versions_and_order(client, auth_headers):
    body = client.get("/api/v1/analysis/feature-schema", headers=auth_headers).json()
    assert set(body["extractors"]) == {"face", "motion", "voice"}
    assert body["integration"]["feature_order"] == [f"{m}.{k}" for m, k in INTEGRATION_FEATURES]


def test_integration_schema_label_comes_from_inputs(client, auth_headers, db):
    from app.models import FacialMeasurement

    sid = new_session(client, auth_headers, face=True, motion=False, voice=True)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    face = db.scalars(select(FacialMeasurement)).one()
    face.feature_schema_version = "1.0"  # simulate a measurement captured before schema 1.1
    db.commit()

    legacy = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert legacy["feature_schema_version"] == "1.0"

    post_voice(client, auth_headers, sid)  # current schema (1.1)
    mixed = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert mixed["feature_schema_version"] == "mixed"
    assert {s["modality"]: s["feature_schema_version"] for s in mixed["source_measurements"]} == {
        "face": "1.0", "voice": "1.1"
    }
    # Saving new records never relabels earlier ones.
    db.expire_all()
    assert db.get(CombinedResult, legacy["id"]).feature_schema_version == "1.0"


def test_integration_schema_label_matches_current_inputs(client, auth_headers):
    sid = new_session(client, auth_headers)
    capture_all(client, auth_headers, sid)
    rec = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()
    assert rec["feature_schema_version"] == "1.1"
