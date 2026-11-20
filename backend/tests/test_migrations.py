"""Migrations must build exactly the schema the models describe, and be reversible."""

import argparse

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from app.core.config import BACKEND_DIR
from app.db.base import Base


def _config(conn, *x_args: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False
    config.attributes["connection"] = conn
    config.cmd_opts = argparse.Namespace(x=list(x_args))  # same as `alembic -x key=value`
    return config


def test_upgrade_matches_models_and_downgrade_is_clean(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migrations.db'}")
    with engine.begin() as conn:
        command.upgrade(_config(conn), "head")

    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
        assert diff == [], f"Models and migrations differ: {diff}"

    with engine.begin() as conn:
        command.downgrade(_config(conn), "base")
    with engine.connect() as conn:
        assert set(inspect(conn).get_table_names()) <= {"alembic_version"}
    engine.dispose()


def test_0002_preserves_existing_measurements(tmp_path):
    """Rows created under 0001 survive 0002 unchanged; their extractor_version stays NULL (not invented)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    with engine.begin() as conn:
        command.upgrade(_config(conn), "0001")
        conn.execute(text(
            "INSERT INTO analysis_sessions (id, reference_code, subject_label, status, created_at, updated_at) "
            "VALUES (1, 'VN-OLD', 'old', 'in_progress', '2026-10-01 10:00:00', '2026-10-01 10:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO voice_measurements (id, session_id, source, quality_score, is_reliable, "
            "feature_schema_version, features, warnings, captured_at, created_at) "
            "VALUES (7, 1, 'upload', 0.9, 1, '1.0', '{\"f0_median_hz\": 180.0}', '[]', "
            "'2026-10-01 10:01:00', '2026-10-01 10:01:00')"
        ))
        command.upgrade(_config(conn), "head")
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT session_id, quality_score, features, extractor_version FROM voice_measurements WHERE id = 7"
        )).one()
        assert row.session_id == 1 and row.quality_score == 0.9
        assert '"f0_median_hz": 180.0' in row.features
        assert row.extractor_version is None
    engine.dispose()


def _db_with_saved_integration(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'guard.db'}")
    with engine.begin() as conn:
        command.upgrade(_config(conn), "0002")
        conn.execute(text(
            "INSERT INTO analysis_sessions (id, reference_code, subject_label, status, created_at, updated_at) "
            "VALUES (1, 'VN-G', 'guard', 'in_progress', '2026-10-01 10:00:00', '2026-10-01 10:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO combined_results (id, session_id, mode, modalities_used, explanation, limitations, "
            "created_at) VALUES (5, 1, 'feature_integration', '[\"face\"]', '{}', '[]', '2026-10-01 10:02:00')"
        ))
    return engine


def _state(engine):
    with engine.connect() as conn:
        return (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
            conn.execute(text("SELECT COUNT(*) FROM combined_results")).scalar_one(),
        )


def test_0002_downgrade_refuses_to_delete_saved_records(tmp_path):
    engine = _db_with_saved_integration(tmp_path)
    with pytest.raises(RuntimeError) as err, engine.begin() as conn:
        command.downgrade(_config(conn), "0001")
    message = str(err.value)
    assert "would delete 1 saved combined record(s)" in message
    assert "scripts.backup_db" in message and "-x allow_data_loss=true" in message
    assert _state(engine) == ("0002", 1)  # nothing changed
    engine.dispose()


def test_0002_downgrade_with_explicit_override_deletes_them(tmp_path):
    engine = _db_with_saved_integration(tmp_path)
    with engine.begin() as conn:
        command.downgrade(_config(conn, "allow_data_loss=true"), "0001")
    assert _state(engine) == ("0001", 0)
    engine.dispose()


@pytest.mark.parametrize("value", ["false", "yes", "1", ""])
def test_0002_downgrade_override_must_be_exactly_true(tmp_path, value):
    engine = _db_with_saved_integration(tmp_path)
    with pytest.raises(RuntimeError), engine.begin() as conn:
        command.downgrade(_config(conn, f"allow_data_loss={value}"), "0001")
    assert _state(engine) == ("0002", 1)
    engine.dispose()


def test_0003_upgrade_marks_existing_sessions_real(tmp_path):
    engine = _db_with_saved_integration(tmp_path)
    with engine.begin() as conn:
        command.upgrade(_config(conn), "0003")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT is_synthetic FROM analysis_sessions WHERE id = 1")).scalar_one() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM combined_results")).scalar_one() == 1
    engine.dispose()


def _db_at_0003_with_synthetic(tmp_path):
    engine = _db_with_saved_integration(tmp_path)  # session 1 (real) + its combined record 5
    with engine.begin() as conn:
        command.upgrade(_config(conn), "0003")
        conn.execute(text(
            "INSERT INTO analysis_sessions (id, reference_code, subject_label, status, is_synthetic, created_at, "
            "updated_at) VALUES (2, 'VN-S', 'SYNTHETIC', 'in_progress', 1, '2026-10-01 10:00:00', '2026-10-01 10:00:00')"
        ))
    return engine


def test_0003_downgrade_refuses_while_synthetic_data_exists(tmp_path):
    engine = _db_at_0003_with_synthetic(tmp_path)
    with pytest.raises(RuntimeError) as err, engine.begin() as conn:
        command.downgrade(_config(conn), "0002")
    assert "1 synthetic demo session(s)" in str(err.value) and "-x allow_data_loss=true" in str(err.value)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003"
        assert conn.execute(text("SELECT COUNT(*) FROM analysis_sessions")).scalar_one() == 2
    engine.dispose()


def test_0003_downgrade_override_removes_only_synthetic_sessions(tmp_path):
    engine = _db_at_0003_with_synthetic(tmp_path)
    with engine.begin() as conn:
        command.downgrade(_config(conn, "allow_data_loss=true"), "0002")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002"
        # The real session and its combined record survive; the synthetic one cannot become "real".
        assert conn.execute(text("SELECT id FROM analysis_sessions")).scalars().all() == [1]
        assert conn.execute(text("SELECT COUNT(*) FROM combined_results")).scalar_one() == 1
    engine.dispose()


def test_0003_downgrade_without_synthetic_data_needs_no_override(tmp_path):
    engine = _db_with_saved_integration(tmp_path)
    with engine.begin() as conn:
        command.upgrade(_config(conn), "0003")
        command.downgrade(_config(conn), "0002")
    assert _state(engine) == ("0002", 1)
    engine.dispose()
