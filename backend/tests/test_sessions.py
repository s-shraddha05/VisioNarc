import csv
import io

import pytest
from sqlalchemy import func, select

from app.models import AnalysisSession, ConsentRecord, FacialMeasurement
from tests.conftest import TEST_ADMIN_USERNAME

URL = "/api/v1/sessions"


def payload(label="Participant 01", **consent):
    base = {"consent_given": True, "consented_by_label": "P01", "allow_face": True}
    base.update(consent)
    return {"subject_label": label, "notes": "  pilot run  ", "consent": base}


def create(client, headers, **kwargs):
    response = client.post(URL, json=payload(**kwargs), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_sessions_require_auth(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=payload()).status_code == 401
    assert client.get(f"{URL}/1").status_code == 401
    assert client.delete(f"{URL}/1").status_code == 401
    assert client.get(f"{URL}/export.csv").status_code == 401


def test_create_session_records_consent(client, auth_headers, db, settings):
    body = create(client, auth_headers, allow_voice=True, allow_raw_media_storage=True)
    assert body["reference_code"].startswith("VN-")
    assert body["status"] == "consented"
    assert body["notes"] == "pilot run"
    assert body["created_by"] == TEST_ADMIN_USERNAME
    assert body["allow_face"] and body["allow_voice"] and not body["allow_motion"]
    assert body["counts"] == {"face": 0, "motion": 0, "voice": 0, "results": 0}
    consent = body["consent"]
    assert consent["consent_given"] is True
    assert consent["consent_text_version"] == "1.0"
    # STORE_RAW_MEDIA is false in tests, so raw-media consent is not honoured.
    assert consent["allow_raw_media_storage"] is False
    assert body["retain_until"] is not None
    assert body["facial_measurements"] == [] and body["combined_results"] == []


@pytest.mark.parametrize(
    "bad",
    [
        {"subject_label": "   "},
        {"consent": {"consent_given": False, "consented_by_label": "x", "allow_face": True}},
        {"consent": {"consent_given": True, "consented_by_label": "x"}},  # no modality
        {"consent": {"consent_given": True, "consented_by_label": "", "allow_face": True}},
        {"notes": "x" * 2001},
    ],
)
def test_create_session_validation(client, auth_headers, db, bad):
    response = client.post(URL, json={**payload(), **bad}, headers=auth_headers)
    assert response.status_code == 422
    assert db.scalar(select(func.count(AnalysisSession.id))) == 0


def test_list_pagination_search_and_filters(client, auth_headers):
    for i in range(5):
        create(client, auth_headers, label=f"Subject {i}")
    page1 = client.get(URL, params={"page": 1, "page_size": 2}, headers=auth_headers).json()
    assert page1["total"] == 5 and len(page1["items"]) == 2
    # Newest first
    assert page1["items"][0]["subject_label"] == "Subject 4"
    page3 = client.get(URL, params={"page": 3, "page_size": 2}, headers=auth_headers).json()
    assert len(page3["items"]) == 1

    found = client.get(URL, params={"q": "subject 3"}, headers=auth_headers).json()
    assert [s["subject_label"] for s in found["items"]] == ["Subject 3"]

    by_status = client.get(
        URL, params=[("status", "consented"), ("status", "in_progress")], headers=auth_headers
    ).json()
    assert by_status["total"] == 5
    assert client.get(URL, params={"status": "completed"}, headers=auth_headers).json()["total"] == 0
    assert client.get(URL, params={"status": "bogus"}, headers=auth_headers).status_code == 422
    assert client.get(URL, params={"page_size": 500}, headers=auth_headers).status_code == 422
    assert client.get(
        URL, params={"date_from": "2030-01-02", "date_to": "2030-01-01"}, headers=auth_headers
    ).status_code == 422


def test_get_detail_and_404(client, auth_headers):
    created = create(client, auth_headers)
    detail = client.get(f"{URL}/{created['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["reference_code"] == created["reference_code"]
    assert client.get(f"{URL}/99999", headers=auth_headers).status_code == 404


def test_withdraw_consent_deletes_measurements(client, auth_headers, db):
    created = create(client, auth_headers)
    db.add(
        FacialMeasurement(
            session_id=created["id"], source="upload", feature_schema_version="test",
            features={"x": 1}, warnings=[],
        )
    )
    db.commit()
    assert client.get(f"{URL}/{created['id']}", headers=auth_headers).json()["counts"]["face"] == 1

    response = client.post(f"{URL}/{created['id']}/withdraw-consent", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["consent_withdrawn"] is True
    assert body["consent"]["withdrawn_at"] is not None
    assert body["counts"]["face"] == 0
    assert client.post(f"{URL}/{created['id']}/withdraw-consent", headers=auth_headers).status_code == 409


def test_delete_cascades(client, auth_headers, db):
    created = create(client, auth_headers)
    assert client.delete(f"{URL}/{created['id']}", headers=auth_headers).status_code == 204
    db.expire_all()
    assert db.get(AnalysisSession, created["id"]) is None
    assert db.scalar(select(func.count(ConsentRecord.id))) == 0
    assert client.delete(f"{URL}/{created['id']}", headers=auth_headers).status_code == 404


def test_json_export(client, auth_headers):
    created = create(client, auth_headers)
    response = client.get(f"{URL}/{created['id']}/export", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["app"].startswith("VisoNarc")
    assert "cannot prove drug consumption" in body["disclaimer"]
    assert body["session"]["reference_code"] == created["reference_code"]


def test_csv_export_escapes_formulas(client, auth_headers):
    create(client, auth_headers, label="=HYPERLINK(\"x\")")
    response = client.get(f"{URL}/export.csv", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.text.lstrip("﻿"))))
    assert rows[1][0] == "reference_code"
    assert rows[2][1].startswith("'=")


def test_csv_and_list_carry_no_indicator_fields(client, auth_headers):
    create(client, auth_headers)
    rows = list(csv.reader(io.StringIO(client.get(f"{URL}/export.csv", headers=auth_headers).text.lstrip("﻿"))))
    assert rows[1] == [
        "reference_code", "subject_label", "status", "created_at_utc", "completed_at_utc",
        "retain_until_utc", "created_by", "consent_face", "consent_motion", "consent_voice",
        "consent_withdrawn", "face_measurements", "motion_measurements", "voice_measurements",
        "combined_results",
    ]
    assert all(len(r) == len(rows[1]) for r in rows[2:])
    item = client.get(URL, headers=auth_headers).json()["items"][0]
    assert not any("indicator" in key for key in item)


def test_session_actions_are_audited(client, auth_headers):
    created = create(client, auth_headers)
    client.get(f"{URL}/{created['id']}/export", headers=auth_headers)
    client.delete(f"{URL}/{created['id']}", headers=auth_headers)
    actions = client.get("/api/v1/audit-logs/actions", headers=auth_headers).json()
    assert {"session.created", "session.exported_json", "session.deleted"} <= set(actions)
