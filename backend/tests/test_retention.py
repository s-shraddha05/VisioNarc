"""Retention purge, scheduler, CLI and measurement deletion. Disposable in-memory SQLite only."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.base import utcnow
from app.db.session import get_db
from app.main import create_app
from app.models import (
    AnalysisSession,
    AuditLog,
    CombinedResult,
    ConsentRecord,
    FacialMeasurement,
    VoiceMeasurement,
)
from app.services import retention_service
from tests.analysis_fixtures import face_payload
from tests.test_analysis_api import SESSIONS, new_session, post_voice


def expire(db, sid, days_ago=1):
    db.expire_all()
    s = db.get(AnalysisSession, sid)
    s.retain_until = utcnow() - timedelta(days=days_ago)
    db.commit()


def populated(client, headers):
    sid = new_session(client, headers)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=headers)
    post_voice(client, headers, sid)
    client.post(f"{SESSIONS}/{sid}/integrations", headers=headers)
    return sid


def counts(db, sid):
    db.expire_all()
    return {
        m.__name__: db.scalar(select(func.count()).select_from(m).where(m.session_id == sid))
        for m in (ConsentRecord, FacialMeasurement, VoiceMeasurement, CombinedResult)
    }


def test_retention_endpoints_require_auth(client):
    assert client.get("/api/v1/retention/preview").status_code == 401
    assert client.post("/api/v1/retention/purge", json={"session_ids": [1], "confirm": True}).status_code == 401


def test_preview_lists_only_expired_with_dependents(client, auth_headers, db):
    old = populated(client, auth_headers)
    keep = populated(client, auth_headers)
    no_date = new_session(client, auth_headers)
    expire(db, old)
    db.get(AnalysisSession, no_date).retain_until = None
    db.commit()

    body = client.get("/api/v1/retention/preview", headers=auth_headers).json()
    assert [s["id"] for s in body["sessions"]] == [old]
    s = body["sessions"][0]
    assert (s["consent_records"], s["face_measurements"], s["voice_measurements"], s["combined_records"]) == (1, 1, 1, 1)
    assert body["auto_purge_enabled"] is False and body["retention_days"] == 90
    assert keep not in [x["id"] for x in body["sessions"]]


def test_manual_purge_is_confirmed_scoped_cascading_audited_and_repeatable(client, auth_headers, db):
    old = populated(client, auth_headers)
    keep = populated(client, auth_headers)
    expire(db, old)
    before_keep = counts(db, keep)

    assert client.post("/api/v1/retention/purge", json={"session_ids": [old]}, headers=auth_headers).status_code == 422
    assert client.post("/api/v1/retention/purge", json={"session_ids": [old], "confirm": False},
                       headers=auth_headers).status_code == 422

    res = client.post("/api/v1/retention/purge", json={"session_ids": [old, keep], "confirm": True},
                      headers=auth_headers).json()
    assert [d["id"] for d in res["deleted"]] == [old]
    assert res["skipped_ids"] == [keep]  # not expired: never deleted even if requested
    assert db.get(AnalysisSession, old) is None
    assert counts(db, old) == {"ConsentRecord": 0, "FacialMeasurement": 0, "VoiceMeasurement": 0, "CombinedResult": 0}
    assert counts(db, keep) == before_keep  # other sessions untouched

    log = db.scalars(select(AuditLog).where(AuditLog.action == "retention.purged")).one()
    assert log.details["trigger"] == "manual" and log.details["count"] == 1
    assert set(log.details) == {"trigger", "count", "reference_codes"}

    again = client.post("/api/v1/retention/purge", json={"session_ids": [old], "confirm": True},
                        headers=auth_headers).json()
    assert again == {"deleted": [], "skipped_ids": [old]}


def test_purge_rolls_back_if_sessions_change_mid_purge(client, auth_headers, db, monkeypatch):
    a = populated(client, auth_headers)
    b = populated(client, auth_headers)
    expire(db, a)
    real = retention_service.find_expired

    def stale(session, now=None):
        found = real(session, now)
        # Pretend b was expired at preview time, but it is not when the DELETE runs.
        return found + [retention_service.ExpiredSession(b, "x", "x", "x", utcnow(), 1, 1, 0, 1, 1)]

    monkeypatch.setattr(retention_service, "find_expired", stale)
    res = client.post("/api/v1/retention/purge", json={"session_ids": [a, b], "confirm": True}, headers=auth_headers)
    assert res.status_code == 409
    db.expire_all()
    assert db.get(AnalysisSession, a) is not None and db.get(AnalysisSession, b) is not None  # nothing deleted


def _app_with(settings, session_factory, **overrides):
    s = settings.model_copy(update=overrides)
    app = create_app(s, session_factory=session_factory)

    def _get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_settings] = lambda: s
    return app


def test_automatic_purge_runs_at_startup_when_enabled(client, auth_headers, db, settings, session_factory):
    old = populated(client, auth_headers)
    keep = populated(client, auth_headers)
    expire(db, old)
    app = _app_with(settings, session_factory, retention_auto_purge=True)
    with TestClient(app) as c:
        token = c.post("/api/v1/auth/login", json={"username": "testadmin", "password": "Test-Password-2026"}).json()
        body = c.get("/api/v1/retention/preview", headers={"Authorization": f"Bearer {token['access_token']}"}).json()
    assert body["auto_purge_enabled"] is True
    assert body["last_automatic_run"]["deleted"] == 1 and body["last_automatic_run"]["error"] is None
    db.expire_all()
    assert db.get(AnalysisSession, old) is None and db.get(AnalysisSession, keep) is not None
    log = db.scalars(select(AuditLog).where(AuditLog.action == "retention.purged")).one()
    assert log.details["trigger"] == "automatic" and log.admin_id is None


def test_automatic_purge_disabled_by_default(client, auth_headers, db, settings, session_factory):
    old = populated(client, auth_headers)
    expire(db, old)
    with TestClient(_app_with(settings, session_factory)):
        pass
    db.expire_all()
    assert db.get(AnalysisSession, old) is not None


def test_automatic_purge_failure_does_not_stop_the_api(settings):
    def broken():
        raise RuntimeError("db down")

    app = _app_with(settings, broken, retention_auto_purge=True)
    with TestClient(app) as c:
        assert c.get("/api/v1/health").status_code == 200
        assert app.state.retention_scheduler.last_run["error"] == "RuntimeError"


def test_cli_dry_run_then_apply(client, auth_headers, db, session_factory, monkeypatch, capsys):
    import scripts.purge_expired as cli

    old = populated(client, auth_headers)
    expire(db, old)
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: session_factory)

    monkeypatch.setattr("sys.argv", ["purge_expired"])
    assert cli.main() == 0
    assert "Dry run only" in capsys.readouterr().out
    db.expire_all()
    assert db.get(AnalysisSession, old) is not None

    monkeypatch.setattr("sys.argv", ["purge_expired", "--apply", "--yes"])
    assert cli.main() == 0
    assert "Deleted 1 session(s)" in capsys.readouterr().out
    db.expire_all()
    assert db.get(AnalysisSession, old) is None


def test_delete_measurement_removes_dependent_records_only(client, auth_headers, db):
    sid = new_session(client, auth_headers)
    face = client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers).json()
    voice = post_voice(client, auth_headers, sid).json()
    with_face = client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers).json()

    other = new_session(client, auth_headers)
    other_voice = post_voice(client, auth_headers, other).json()

    assert client.delete(f"{SESSIONS}/{sid}/measurements/face/{face['id']}").status_code == 401
    assert client.delete(f"{SESSIONS}/{other}/measurements/face/{face['id']}", headers=auth_headers).status_code == 404
    assert client.delete(f"{SESSIONS}/{sid}/measurements/gait/{face['id']}", headers=auth_headers).status_code == 422

    res = client.delete(f"{SESSIONS}/{sid}/measurements/face/{face['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == {"modality": "face", "measurement_id": face["id"], "removed_combined_records": [with_face["id"]]}
    db.expire_all()
    assert db.get(FacialMeasurement, face["id"]) is None
    assert db.get(VoiceMeasurement, voice["id"]) is not None
    assert db.get(VoiceMeasurement, other_voice["id"]) is not None
    log = db.scalars(select(AuditLog).where(AuditLog.action == "measurement.deleted")).one()
    assert set(log.details) == {"modality", "measurement_id", "removed_combined_records"}
    assert client.delete(f"{SESSIONS}/{sid}/measurements/face/{face['id']}", headers=auth_headers).status_code == 404


@pytest.mark.parametrize("days_ago, expected", [(1, True), (-1, False)])
def test_find_expired_boundary(client, auth_headers, db, days_ago, expected):
    sid = new_session(client, auth_headers)
    expire(db, sid, days_ago=days_ago)
    assert (sid in [e.id for e in retention_service.find_expired(db)]) is expected
