"""PDF session report (ReportLab). Synthetic fixture data only."""

from sqlalchemy import select

from app.models import AuditLog
from tests.analysis_fixtures import face_payload
from tests.test_analysis_api import SESSIONS, new_session, post_voice


def pdf(client, headers, sid):
    return client.get(f"{SESSIONS}/{sid}/report.pdf", headers=headers)


def test_report_requires_auth_and_existing_session(client, auth_headers):
    assert client.get(f"{SESSIONS}/1/report.pdf").status_code == 401
    assert pdf(client, auth_headers, 999).status_code == 404


def test_empty_session_report(client, auth_headers):
    sid = new_session(client, auth_headers)
    response = pdf(client, auth_headers, sid)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith('attachment; filename="visonarc-VN-')
    body = response.content
    assert body.startswith(b"%PDF-") and body.rstrip().endswith(b"%%EOF")
    assert b"No measurements recorded for this modality." in body
    assert b"No combined records saved for this session." in body
    assert b"cannot establish drug use" in body


def test_full_report_contents_and_audit(client, auth_headers, db):
    sid = new_session(client, auth_headers, face=True, motion=False, voice=True)
    face = client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers).json()
    post_voice(client, auth_headers, sid)
    client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    body = pdf(client, auth_headers, sid).content

    assert f"Measurement #{face['id']}".encode() in body
    assert b"face/1.1.0+mp-tasks-vision-1.1.0" in body  # extractor provenance
    assert b"Saved combined records" in body and b"Record #" in body
    assert b"Not consented" in body  # motion slot status in the saved record
    assert b"Limitations" in body
    # Never raw media; never invented score fields.
    assert b"RIFF" not in body
    assert b"indicator_score" not in body and b"confidence:" not in body

    log = db.scalars(select(AuditLog).where(AuditLog.action == "session.report_pdf")).one()
    assert set(log.details) == {"reference_code", "bytes"}  # no report contents in the audit log


def test_withdrawn_session_report_still_generates(client, auth_headers):
    sid = new_session(client, auth_headers)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    client.post(f"{SESSIONS}/{sid}/withdraw-consent", headers=auth_headers)
    body = pdf(client, auth_headers, sid).content
    assert body.startswith(b"%PDF-")
    assert b"No measurements recorded for this modality." in body


def test_text_sanitising_handles_unsupported_glyphs():
    from app.services.report_service import _text

    assert _text("≥ 30 px & <tag>") == "&gt;= 30 px &amp; &lt;tag&gt;"
    assert _text("中") == "?"  # outside the built-in font's character set


def test_report_states_schema_of_combined_record(client, auth_headers, db):
    from app.models import FacialMeasurement

    sid = new_session(client, auth_headers, face=True, motion=False, voice=True)
    client.post(f"{SESSIONS}/{sid}/analysis/face", json=face_payload(), headers=auth_headers)
    db.scalars(select(FacialMeasurement)).one().feature_schema_version = "1.0"  # legacy input
    db.commit()
    post_voice(client, auth_headers, sid)
    client.post(f"{SESSIONS}/{sid}/integrations", headers=auth_headers)
    body = pdf(client, auth_headers, sid).content
    assert rb"mixed feature schemas \(see sources\)" in body  # PDF strings escape parentheses
    assert b"schema 1.0" in body and b"schema 1.1" in body  # each source keeps its own version
