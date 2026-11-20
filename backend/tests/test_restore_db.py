"""Guards of scripts/restore_db.py. No MySQL needed: the database, backup and mysql client are faked.

The real restore path is exercised against a throwaway MySQL server (see docs/BUILD_STATUS.md).
"""

import pytest

from app.core.config import Settings
from scripts import restore_db

DUMP = b"""-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: visonarc
-- ------------------------------------------------------
DROP TABLE IF EXISTS `admins`;
CREATE TABLE `admins` (
  `id` int NOT NULL AUTO_INCREMENT
);
DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL
);
LOCK TABLES `alembic_version` WRITE;
INSERT INTO `alembic_version` VALUES ('0002');
UNLOCK TABLES;
"""


@pytest.fixture
def env(monkeypatch, tmp_path):
    calls = {"backup": 0, "mysql": 0}
    settings = Settings(_env_file=None, jwt_secret_key="s" * 40, db_name="visonarc", db_password="pw")
    monkeypatch.setattr(restore_db, "get_settings", lambda: settings)
    monkeypatch.setattr(restore_db, "current_state", lambda: (["admins", "alembic_version", "extra"], "0002"))
    monkeypatch.setattr(restore_db.shutil, "which", lambda _: "mysql.exe")

    def fake_backup():
        calls["backup"] += 1
        return calls.get("backup_result", 0)

    def fake_run(*_a, **kwargs):
        calls["mysql"] += 1
        calls["script"] = kwargs.get("input", b"")

        class Done:
            returncode = 0
            stderr = b""
        return Done()

    monkeypatch.setattr(restore_db.backup_db, "main", fake_backup)
    monkeypatch.setattr(restore_db.subprocess, "run", fake_run)
    dump = tmp_path / "visonarc-20261026.sql"
    dump.write_bytes(DUMP)
    return calls, dump


def test_read_dump_finds_database_tables_and_revision(tmp_path):
    path = tmp_path / "d.sql"
    path.write_bytes(DUMP)
    info = restore_db.read_dump(path)
    assert info.database == "visonarc"
    assert info.tables == ["admins", "alembic_version"]
    assert info.revision == "0002"


def test_dry_run_changes_nothing(env, capsys):
    calls, dump = env
    assert restore_db.main([str(dump)]) == 0
    out = capsys.readouterr().out
    assert "Dry run only" in out and "Tables dropped  : extra" in out
    assert calls == {"backup": 0, "mysql": 0}
    assert "pw" not in out  # credentials are never printed


def test_apply_requires_typing_the_database_name(env, monkeypatch, capsys):
    calls, dump = env
    monkeypatch.setattr("builtins.input", lambda _prompt: "visonarc_typo")
    assert restore_db.main([str(dump), "--apply"]) == 1
    assert "Nothing was restored" in capsys.readouterr().out
    assert calls == {"backup": 0, "mysql": 0}


def test_apply_backs_up_first_and_aborts_if_that_fails(env, monkeypatch, capsys):
    calls, dump = env
    calls["backup_result"] = 1
    monkeypatch.setattr("builtins.input", lambda _prompt: "visonarc")
    assert restore_db.main([str(dump), "--apply"]) == 1
    assert "Pre-restore backup failed" in capsys.readouterr().out
    assert calls["backup"] == 1 and calls["mysql"] == 0


def test_apply_restores_after_backup(env, monkeypatch, capsys):
    calls, dump = env
    monkeypatch.setattr("builtins.input", lambda _prompt: "visonarc")
    assert restore_db.main([str(dump), "--apply"]) == 0
    assert calls["backup"] == 1 and calls["mysql"] == 1
    # Tables missing from the backup are dropped first, then the backup is loaded.
    assert calls["script"].startswith(b"SET FOREIGN_KEY_CHECKS=0;\nDROP TABLE IF EXISTS `extra`;\n")
    # LOCK TABLES needs a privilege the app user does not have; the statements are stripped.
    assert b"LOCK TABLES" not in calls["script"]
    assert b"INSERT INTO `alembic_version` VALUES ('0002');" in calls["script"]
    assert "Restore complete" in capsys.readouterr().out


@pytest.mark.parametrize(
    "content, message",
    [
        (b"SELECT 1;", "not a mysqldump backup"),
        (DUMP.replace(b"Database: visonarc", b"Database: otherdb"), "not the configured 'visonarc'"),
        (DUMP.replace(b"`alembic_version`", b"`other`"), "no alembic_version table"),
    ],
    ids=["not-a-dump", "other-database", "incomplete"],
)
def test_unsuitable_backups_are_refused(env, capsys, content, message):
    calls, dump = env
    dump.write_bytes(content)
    assert restore_db.main([str(dump), "--apply"]) == 1
    assert message in capsys.readouterr().out
    assert calls == {"backup": 0, "mysql": 0}
