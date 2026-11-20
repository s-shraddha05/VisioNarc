"""End-to-end API workflow on a disposable in-memory database.

Inputs are SYNTHETIC test fixtures (generated landmarks and a generated tone). Passing this test shows
the software path works end to end; it says nothing about real-world scientific validity.
"""

from sqlalchemy import select

from app.models import AuditLog
from tests.analysis_fixtures import face_payload, pose_payload, voice_wav
from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME

API = "/api/v1"


def test_full_workflow_from_sign_in_to_withdrawal_and_sign_out(client, admin, db):
    # 1. Sign in
    r = client.post(f"{API}/auth/login", json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 2-3. Create a session with consent for all modalities
    r = client.post(f"{API}/sessions", headers=h, json={
        "subject_label": "E2E synthetic participant",
        "consent": {"consent_given": True, "consented_by_label": "E2E", "allow_face": True,
                    "allow_motion": True, "allow_voice": True},
    })
    assert r.status_code == 201 and r.json()["status"] == "consented"
    sid, ref = r.json()["id"], r.json()["reference_code"]

    # 4-6. One measurement per modality through the real extraction endpoints
    face = client.post(f"{API}/sessions/{sid}/analysis/face", headers=h, json=face_payload())
    motion = client.post(f"{API}/sessions/{sid}/analysis/motion", headers=h, json=pose_payload())
    voice = client.post(
        f"{API}/sessions/{sid}/analysis/voice", params={"source": "upload", "upload_consent": "true"},
        headers={**h, "Content-Type": "audio/wav"}, content=voice_wav(),
    )
    assert (face.status_code, motion.status_code, voice.status_code) == (201, 201, 201)
    assert all(m.json()["is_reliable"] and m.json()["extractor_version"] for m in (face, motion, voice))

    # 7. Saved measurements are visible on the session
    detail = client.get(f"{API}/sessions/{sid}", headers=h).json()
    assert detail["status"] == "in_progress"
    assert detail["counts"] == {"face": 1, "motion": 1, "voice": 1, "results": 0}

    # 8-9. Save a combined record: 14 ordered slots, all measured, provenance and sources present
    rec = client.post(f"{API}/sessions/{sid}/integrations", headers=h).json()
    assert rec["processing_status"] == "complete" and len(rec["features"]) == 14
    assert all(f["status"] == "measured" for f in rec["features"])
    assert {s["measurement_id"] for s in rec["source_measurements"]} == {face.json()["id"], motion.json()["id"], voice.json()["id"]}
    assert rec["indicator_score"] is None and rec["confidence"] is None

    # 10. Summary shows all three modalities available
    summary = client.get(f"{API}/sessions/{sid}/multimodal-summary", headers=h).json()
    assert summary["available_modalities"] == ["face", "motion", "voice"] and summary["missing_modalities"] == []

    # 11. History, reports (JSON, CSV, PDF)
    history = client.get(f"{API}/sessions", params={"q": ref}, headers=h).json()
    assert history["total"] == 1 and history["items"][0]["counts"]["results"] == 1
    assert client.get(f"{API}/sessions/{sid}/export", headers=h).status_code == 200
    assert client.get(f"{API}/sessions/export.csv", headers=h).status_code == 200
    report = client.get(f"{API}/sessions/{sid}/report.pdf", headers=h)
    assert report.status_code == 200 and report.content.startswith(b"%PDF-")

    # Withdrawal deletes measurements and the combined record but keeps the session as evidence
    w = client.post(f"{API}/sessions/{sid}/withdraw-consent", headers=h).json()
    assert w["status"] == "cancelled" and w["counts"] == {"face": 0, "motion": 0, "voice": 0, "results": 0}
    assert client.post(f"{API}/sessions/{sid}/analysis/face", headers=h, json=face_payload()).status_code == 409

    # 12. Audit trail records each step in order, without feature values
    actions = [a for (a,) in db.execute(select(AuditLog.action).order_by(AuditLog.id)).all()]
    expected = [
        "auth.login", "session.created", "analysis.face_measured", "analysis.motion_measured",
        "analysis.voice_measured", "analysis.integration_recorded", "session.exported_json",
        "session.exported_csv", "session.report_pdf", "session.consent_withdrawn",
    ]
    positions = [actions.index(a) for a in expected]
    assert positions == sorted(positions)
    for log in db.scalars(select(AuditLog)).all():
        assert "features" not in (log.details or {})

    # 13. Sign out: the token stops working; signing in again works
    assert client.post(f"{API}/auth/logout", headers=h).status_code == 200
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    again = client.post(f"{API}/auth/login", json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD})
    assert again.status_code == 200
