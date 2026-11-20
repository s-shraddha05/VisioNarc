from datetime import timedelta

from app.db.base import utcnow
from app.models import AnalysisSession

NEW_SESSION = {
    "subject_label": "Participant",
    "consent": {"consent_given": True, "consented_by_label": "P", "allow_voice": True},
}


def test_new_endpoints_require_auth(client):
    for path in ("/api/v1/dashboard/summary", "/api/v1/audit-logs", "/api/v1/audit-logs/actions",
                 "/api/v1/settings"):
        assert client.get(path).status_code == 401, path
    assert client.patch("/api/v1/auth/me", json={"full_name": "x"}).status_code == 401


def test_dashboard_empty_is_all_zero(client, auth_headers):
    body = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    assert body["totals"] == {
        "sessions": 0, "active_sessions": 0, "completed_sessions": 0, "face_measurements": 0,
        "motion_measurements": 0, "voice_measurements": 0, "combined_results": 0,
    }
    assert body["sessions_by_status"] == {}
    assert len(body["sessions_per_day"]) == 14
    assert all(d["count"] == 0 for d in body["sessions_per_day"])
    # The login made by the fixture is real activity.
    assert body["recent_activity"][0]["action"] == "auth.login"


def test_dashboard_counts_real_rows(client, auth_headers, db):
    client.post("/api/v1/sessions", json=NEW_SESSION, headers=auth_headers)
    client.post("/api/v1/sessions", json=NEW_SESSION, headers=auth_headers)
    old = AnalysisSession(reference_code="VN-OLD", subject_label="old", status="completed",
                          created_at=utcnow() - timedelta(days=40))
    db.add(old)
    db.commit()

    body = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    assert body["totals"]["sessions"] == 3
    assert body["totals"]["active_sessions"] == 2
    assert body["totals"]["completed_sessions"] == 1
    assert body["sessions_by_status"] == {"consented": 2, "completed": 1}
    assert sum(d["count"] for d in body["sessions_per_day"]) == 2  # the 40-day-old one is outside
    assert body["sessions_per_day"][-1]["count"] == 2
    assert client.get("/api/v1/dashboard/summary?days=3", headers=auth_headers).status_code == 422


def test_audit_log_listing_and_filters(client, auth_headers):
    client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong-pass-1"})
    body = client.get("/api/v1/audit-logs", headers=auth_headers).json()
    assert body["total"] >= 3  # admin.created, auth.login, auth.login_failed
    assert body["items"][0]["action"] == "auth.login_failed"

    auth_only = client.get("/api/v1/audit-logs", params={"action": "auth"}, headers=auth_headers).json()
    assert {i["action"] for i in auth_only["items"]} == {"auth.login", "auth.login_failed"}
    exact = client.get("/api/v1/audit-logs", params={"action": "auth.login"}, headers=auth_headers).json()
    assert {i["action"] for i in exact["items"]} == {"auth.login"}
    assert exact["items"][0]["admin_username"] == "testadmin"

    paged = client.get("/api/v1/audit-logs", params={"page_size": 1, "page": 2}, headers=auth_headers).json()
    assert len(paged["items"]) == 1 and paged["page"] == 2


def test_settings_are_read_only_view(client, auth_headers):
    body = client.get("/api/v1/settings", headers=auth_headers).json()
    assert body["store_raw_media"] is False
    assert body["data_retention_days"] == 90
    assert body["login_max_failed_attempts"] == 3
    # Analysis needs NumPy (Phase 3); PDF reports need ReportLab (Phase 4).
    assert body["capabilities"] == {
        "face_analysis": True, "motion_analysis": True, "voice_analysis": True,
        "multimodal_analysis": True, "pdf_reports": True,
    }
    assert "jwt_secret_key" not in body and "db_password" not in body


def test_profile_update(client, auth_headers):
    response = client.patch("/api/v1/auth/me", json={"full_name": "  Dr.   Research  Admin "},
                            headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Dr. Research Admin"
    assert client.patch("/api/v1/auth/me", json={"full_name": ""}, headers=auth_headers).json()["full_name"] is None
    assert client.patch("/api/v1/auth/me", json={"full_name": "x" * 101}, headers=auth_headers).status_code == 422
