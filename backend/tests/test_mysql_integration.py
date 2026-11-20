"""Opt-in checks against the real MySQL database configured in backend/.env.

Run after scripts\\setup_mysql.ps1:
    $env:VISONARC_TEST_MYSQL = "1"; python -m pytest -m mysql
Read-only: nothing is written to the database.
"""

import os

import pytest
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from app.api.routes.health import migration_head
from app.core.config import Settings
from app.db.base import Base

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        os.environ.get("VISONARC_TEST_MYSQL") != "1", reason="set VISONARC_TEST_MYSQL=1 to run"
    ),
]


@pytest.fixture(scope="module")
def mysql_engine():
    # Read backend/.env directly; conftest overrides only affect the test Settings fixture.
    url = Settings(database_url=None).sqlalchemy_url
    engine = create_engine(url)
    yield engine
    engine.dispose()


def test_mysql_version_and_charset(mysql_engine):
    with mysql_engine.connect() as conn:
        assert conn.execute(text("SELECT VERSION()")).scalar_one().startswith("8.")
        assert conn.execute(text("SELECT @@character_set_database")).scalar_one() == "utf8mb4"


def test_mysql_schema_is_migrated(mysql_engine):
    with mysql_engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        assert set(Base.metadata.tables) <= tables
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == migration_head()


def test_mysql_phase2_queries_execute(mysql_engine):
    """Run the Phase 2 list/search/dashboard/audit SELECTs on real MySQL (no writes)."""
    from datetime import date

    from sqlalchemy.orm import Session

    from app.api.routes.audit_logs import recent_events
    from app.services.session_service import get_detail, list_sessions

    with Session(mysql_engine) as db:
        items, total = list_sessions(
            db, page=1, page_size=5, statuses=["consented", "completed"], q="vn",
            date_from=date(2020, 1, 1), date_to=date(2100, 1, 1),
        )
        assert total >= len(items)
        for item in items:
            assert get_detail(db, item.id).reference_code == item.reference_code
        assert isinstance(recent_events(db, limit=5), list)
        from app.api.routes.dashboard import summary

        stats = summary(db=db, _admin=None, days=14)
        assert stats.totals.sessions == sum(stats.sessions_by_status.values())
        db.rollback()


def test_mysql_accepts_feature_integration_rows_and_rejects_bad_modes(mysql_engine):
    """Runs inside a transaction that is always rolled back: nothing is persisted."""
    from sqlalchemy.exc import DBAPIError

    with mysql_engine.connect() as conn:
        session_id = conn.execute(text("SELECT MIN(id) FROM analysis_sessions")).scalar()
        if session_id is None:
            pytest.skip("no analysis session to reference")
        try:  # the SELECT above auto-began a transaction; everything below is rolled back
            insert = text(
                "INSERT INTO combined_results (session_id, mode, modalities_used, indicator_level, explanation, "
                "limitations, processing_status, feature_schema_version, extractor_version, features, "
                "source_measurements, created_at) VALUES (:sid, :mode, '[\"face\"]', NULL, '{}', '[]', 'partial', "
                "'1.1', 'integration/test', '[{\"index\": 0, \"value\": null}]', '[]', NOW())"
            )
            conn.execute(insert, {"sid": session_id, "mode": "feature_integration"})
            with pytest.raises(DBAPIError):
                conn.execute(insert, {"sid": session_id, "mode": "drug_score"})
        finally:
            conn.rollback()
        assert conn.execute(text("SELECT COUNT(*) FROM combined_results WHERE extractor_version = 'integration/test'")).scalar() == 0


def test_mysql_retention_preview_finds_expired_rows_rolled_back(mysql_engine):
    """Inserts an EXPIRED TEST session inside a transaction, previews, then rolls back.

    Only find_expired (SELECT) runs; purge is never called against the real database.
    """
    from sqlalchemy.orm import Session

    from app.services.retention_service import find_expired

    with mysql_engine.connect() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM analysis_sessions")).scalar()
        try:
            conn.execute(text(
                "INSERT INTO analysis_sessions (reference_code, subject_label, status, created_at, updated_at, retain_until) "
                "VALUES ('VN-PYTEST-EXPIRED', 'pytest rolled-back row', 'completed', NOW(), NOW(), "
                "UTC_TIMESTAMP() - INTERVAL 1 DAY)"
            ))
            test_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            conn.execute(text(
                "INSERT INTO facial_measurements (session_id, source, is_reliable, feature_schema_version, features, "
                "warnings, captured_at, created_at, face_detected) VALUES (:sid, 'upload', 1, '1.1', '{}', '[]', NOW(), NOW(), 1)"
            ), {"sid": test_id})
            with Session(bind=conn) as db:
                found = {e.id: e for e in find_expired(db)}
            assert test_id in found and found[test_id].face_measurements == 1
        finally:
            conn.rollback()
        assert conn.execute(text("SELECT COUNT(*) FROM analysis_sessions")).scalar() == before
        assert conn.execute(text("SELECT COUNT(*) FROM analysis_sessions WHERE reference_code = 'VN-PYTEST-EXPIRED'")).scalar() == 0


def test_mysql_pdf_report_for_existing_session_read_only(mysql_engine):
    """Builds a PDF in memory from real data (SELECT only); nothing is written or saved."""
    from sqlalchemy.orm import Session

    from app.services.report_service import build_session_report
    from app.services.session_service import get_detail

    with mysql_engine.connect() as conn:
        session_id = conn.execute(text("SELECT MIN(id) FROM analysis_sessions")).scalar()
        if session_id is None:
            pytest.skip("no analysis session")
        try:
            with Session(bind=conn) as db:
                pdf = build_session_report(get_detail(db, session_id), generated_by="pytest")
        finally:
            conn.rollback()
    assert pdf.startswith(b"%PDF-") and len(pdf) > 2000


def test_mysql_enforces_check_constraints(mysql_engine):
    with mysql_engine.connect() as conn:
        checks = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.CHECK_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA = DATABASE()"
            )
        ).scalar_one()
        assert checks >= 10
