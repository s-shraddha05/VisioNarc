"""Experimental screening: synthetic demo only, never for real sessions, stored once, shown consistently."""

import pytest
from sqlalchemy import select

from app.analysis import screening
from app.analysis.feature_schema import INTEGRATION_FEATURES
from app.core.config import get_settings
from app.models import Admin, AnalysisSession, AuditLog, ScreeningResult
from scripts.seed_synthetic_demo import PROFILES, seed
from tests.analysis_fixtures import face_payload
from tests.test_analysis_api import SESSIONS, new_session


@pytest.fixture
def demo_mode(client, settings):
    """Turn the synthetic demo on for this test only."""
    on = settings.model_copy(update={"screening_mode": "synthetic_demo"})
    client.app.dependency_overrides[get_settings] = lambda: on
    yield on
    client.app.dependency_overrides[get_settings] = lambda: settings


@pytest.fixture
def synthetic(db, settings, auth_headers):
    admin = db.scalars(select(Admin)).one()
    return {s.subject_label: s.id for s in seed(db, settings, admin)}


def screen(client, headers, sid):
    return client.post(f"{SESSIONS}/{sid}/screening", headers=headers)


# ---- pure formula ----------------------------------------------------------------------------


def _features(**values):
    """All 14 features at their documented centre (plausible) values unless overridden."""
    return [
        {"modality": m, "key": k, "value": values.get(f"{m}.{k}", screening.DEMO_FEATURES[(m, k)][2])}
        for m, k in INTEGRATION_FEATURES
    ]


USED = {"face": "used", "motion": "used", "voice": "used"}


def test_formula_is_deterministic_and_bounded():
    feats = _features(**{"face.ear_mean": 0.3, "face.symmetry_index": 0.9, "voice.f0_median_hz": 200.0,
                         "voice.spectral_centroid_hz": 1500.0, "voice.snr_db_estimate": 30.0})
    a = screening.score(feats, "1.1", USED)
    b = screening.score(feats, "1.1", USED)
    assert a == b and a.model_status == "synthetic_demo"
    assert 0.0 <= a.estimate <= 1.0 and a.classification in ("Addict", "Non-Addict")
    assert a.coverage == 1.0


def test_missing_modality_is_not_zero_filled():
    feats = _features(**{"face.symmetry_index": 0.9, "voice.f0_median_hz": 200.0, "voice.spectral_centroid_hz": 1500.0})
    for f in feats:
        if f["modality"] == "motion":
            f["value"] = None
    out = screening.score(feats, "1.1", {**USED, "motion": "missing"})
    assert out.missing_modalities == ["motion"] and out.coverage < 1.0
    assert all(not c["feature"].startswith("motion.") for c in out.contributions)


@pytest.mark.parametrize(
    "mutate, status, reason",
    [
        (lambda f, s: f.reverse(), USED, "order"),
        (lambda f, s: f[0].update(value=float("nan")), USED, "plausible range"),
        (lambda f, s: f[0].update(value="0.3"), USED, "plausible range"),
        (lambda f, s: f[0].update(value=99.0), USED, "plausible range"),
        (lambda f, s: None, {"face": "used", "motion": "missing", "voice": "excluded_low_quality"}, "At least 2"),
    ],
    ids=["wrong-order", "nan", "string", "out-of-range", "one-modality"],
)
def test_invalid_or_insufficient_input_gives_no_score(mutate, status, reason):
    feats = _features(**{"face.symmetry_index": 0.9, "voice.f0_median_hz": 200.0, "voice.spectral_centroid_hz": 1500.0})
    mutate(feats, status)
    out = screening.score(feats, "1.1", status)
    assert out.model_status == "insufficient_input"
    assert out.estimate is None and out.classification is None
    assert reason in " ".join(out.reasons)


@pytest.mark.parametrize("version", ["1.0", "mixed", None])
def test_other_schema_versions_are_refused(version):
    out = screening.score(_features(), version, USED)
    assert out.model_status == "insufficient_input" and out.estimate is None


# ---- API -------------------------------------------------------------------------------------


def test_screening_requires_auth(client):
    assert client.get(f"{SESSIONS}/1/screening").status_code == 401
    assert client.post(f"{SESSIONS}/1/screening").status_code == 401


def test_off_by_default(client, auth_headers, synthetic):
    sid = synthetic[PROFILES[0]["label"]]
    view = client.get(f"{SESSIONS}/{sid}/screening", headers=auth_headers).json()
    assert view["mode"] == "off" and view["can_run"] is False and "turned off" in view["message"]
    r = screen(client, auth_headers, sid)
    assert r.status_code == 409 and "SCREENING_MODE=off" in r.json()["detail"]


def test_real_sessions_never_get_an_estimate(client, auth_headers, db, demo_mode):
    sid = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    view = client.get(f"{SESSIONS}/{sid}/screening", headers=auth_headers).json()
    assert view["model_status"] == "unavailable" and view["can_run"] is False
    assert "No reliable estimate is available" in view["message"]
    r = screen(client, auth_headers, sid)
    assert r.status_code == 409 and "No validated model" in r.json()["detail"]
    assert db.query(ScreeningResult).count() == 0
    # The API cannot mark a session synthetic.
    created = client.post(SESSIONS, headers=auth_headers, json={
        "subject_label": "x", "is_synthetic": True,
        "consent": {"consent_given": True, "consented_by_label": "P", "allow_face": True}})
    assert created.status_code == 422 or created.json().get("is_synthetic") is False


def test_synthetic_demo_result_is_stored_with_provenance(client, auth_headers, db, demo_mode, synthetic):
    sid = synthetic[PROFILES[0]["label"]]
    r = screen(client, auth_headers, sid)
    assert r.status_code == 201, r.text
    res = r.json()
    assert res["model_status"] == "synthetic_demo" and res["is_synthetic"] is True
    assert res["model_name"] == screening.MODEL_NAME and res["model_version"] == screening.MODEL_VERSION
    assert res["feature_schema_version"] == "1.1"
    assert set(res["input_measurement_ids"]) == {"face", "motion", "voice"}
    assert 0 <= res["estimate"] <= 1 and res["classification"] in ("Addict", "Non-Addict")
    assert res["decision_threshold"] == 0.5 and "not a probability" in res["target_definition"]
    detail = client.get(f"{SESSIONS}/{sid}", headers=auth_headers).json()
    assert detail["is_synthetic"] is True
    assert [s["id"] for s in detail["screening_results"]] == [res["id"]]
    assert client.get(f"{SESSIONS}/{sid}/screening", headers=auth_headers).json()["results"][0]["id"] == res["id"]
    log = db.scalars(select(AuditLog).where(AuditLog.action == "screening.synthetic_recorded")).one()
    assert set(log.details) == {"result_id", "model_status"}  # no score in the audit log


def test_profiles_differ_and_face_only_is_insufficient(client, auth_headers, demo_mode, synthetic):
    a = screen(client, auth_headers, synthetic[PROFILES[0]["label"]]).json()
    b = screen(client, auth_headers, synthetic[PROFILES[1]["label"]]).json()
    c = screen(client, auth_headers, synthetic[PROFILES[2]["label"]]).json()
    assert a["estimate"] != b["estimate"]
    assert c["model_status"] == "insufficient_input" and c["estimate"] is None and c["classification"] is None
    assert c["missing_modalities"] == ["motion", "voice"]


def test_screening_needs_a_saved_record_and_consent(client, auth_headers, db, demo_mode, synthetic):
    sid = synthetic[PROFILES[0]["label"]]
    client.post(f"{SESSIONS}/{sid}/withdraw-consent", headers=auth_headers)
    assert screen(client, auth_headers, sid).status_code == 409
    assert client.get(f"{SESSIONS}/999/screening", headers=auth_headers).status_code == 404


def test_withdrawal_and_deletion_remove_screening_results(client, auth_headers, db, demo_mode, synthetic):
    a, b = synthetic[PROFILES[0]["label"]], synthetic[PROFILES[1]["label"]]
    screen(client, auth_headers, a)
    screen(client, auth_headers, b)
    client.post(f"{SESSIONS}/{a}/withdraw-consent", headers=auth_headers)
    face_b = client.get(f"{SESSIONS}/{b}", headers=auth_headers).json()["facial_measurements"][0]["id"]
    client.delete(f"{SESSIONS}/{b}/measurements/face/{face_b}", headers=auth_headers)
    db.expire_all()
    assert db.query(ScreeningResult).count() == 0


def test_pdf_shows_the_same_saved_result(client, auth_headers, demo_mode, synthetic):
    sid = synthetic[PROFILES[0]["label"]]
    res = screen(client, auth_headers, sid).json()
    body = client.get(f"{SESSIONS}/{sid}/report.pdf", headers=auth_headers).content
    assert b"SYNTHETIC DEMONSTRATION" in body
    assert f"Screening result #{res['id']}".encode() in body
    assert f"{res['estimate'] * 100:.1f}".encode() in body
    assert res["classification"].encode() in body
    assert screening.MODEL_VERSION.encode() in body


def test_real_session_pdf_states_no_estimate(client, auth_headers):
    sid = new_session(client, auth_headers)
    body = client.get(f"{SESSIONS}/{sid}/report.pdf", headers=auth_headers).content
    assert b"No reliable estimate is available" in body
    assert b"SYNTHETIC DEMONSTRATION" not in body


def test_seed_refuses_databases_with_real_sessions(client, auth_headers, db, capsys, monkeypatch):
    from scripts import seed_synthetic_demo

    new_session(client, auth_headers)
    monkeypatch.setattr(seed_synthetic_demo, "get_sessionmaker", lambda: lambda: _Ctx(db))
    assert seed_synthetic_demo.main(["--admin", "admin"]) == 1
    assert "contains 1 real session" in capsys.readouterr().out
    assert db.query(AnalysisSession).filter(AnalysisSession.is_synthetic.is_(True)).count() == 0


class _Ctx:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *exc):
        return False
