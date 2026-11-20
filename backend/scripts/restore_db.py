"""Restore the configured MySQL database from a backup made by scripts.backup_db.

Usage (from backend/, venv active):
    python -m scripts.restore_db backups\\visonarc-<timestamp>.sql           # dry run: shows what would happen
    python -m scripts.restore_db backups\\visonarc-<timestamp>.sql --apply   # restore after typing the DB name

Restoring makes the database match the backup: tables in the backup are replaced with its contents
and tables that are not in the backup (for example ones added by a later migration) are dropped. Before
anything is replaced, a fresh backup of the current database is written (scripts.backup_db); if
that fails, nothing is restored. Credentials go through a temporary option file, never the
command line. Exit code 0 = dry run shown or restore completed.
"""

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import inspect, text

from app.core.config import get_settings
from scripts import backup_db

DEFAULT_MYSQL = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe")
HEADER_DB = re.compile(rb"^-- Host: .*Database: (\S+)", re.MULTILINE)
CREATE_TABLE = re.compile(rb"^CREATE TABLE `([^`]+)`", re.MULTILINE)
REVISION = re.compile(rb"INSERT INTO `alembic_version` VALUES \('([^']+)'\)")
SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
# mysqldump adds LOCK TABLES around inserts (a speed-up only). The app user deliberately has no LOCK
# TABLES privilege, so these statements are removed before loading.
TABLE_LOCKS = re.compile(rb"^(?:LOCK TABLES `[^`]+` WRITE|UNLOCK TABLES);\r?\n", re.MULTILINE)


@dataclass
class DumpInfo:
    database: str | None
    tables: list[str] = field(default_factory=list)
    revision: str | None = None


def read_dump(path: Path) -> DumpInfo:
    data = path.read_bytes()
    if b"-- MySQL dump" not in data[:400]:
        raise ValueError("This file is not a mysqldump backup.")
    db = HEADER_DB.search(data[:2000])
    rev = REVISION.search(data)
    return DumpInfo(
        database=db.group(1).decode() if db else None,
        tables=sorted(t.decode() for t in CREATE_TABLE.findall(data)),
        revision=rev.group(1).decode() if rev else None,
    )


def current_state() -> tuple[list[str], str | None]:
    from app.db.session import get_engine

    with get_engine().connect() as conn:
        tables = sorted(inspect(conn).get_table_names())
        revision = None
        if "alembic_version" in tables:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    return tables, revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup", type=Path, help="a .sql file written by scripts.backup_db")
    parser.add_argument("--apply", action="store_true", help="restore (otherwise only a dry run)")
    args = parser.parse_args(argv)

    settings = get_settings()
    if settings.database_url:
        print("DATABASE_URL is set; this script only restores the MySQL DB_* configuration.")
        return 1
    if not args.backup.is_file():
        print(f"Backup file not found: {args.backup}")
        return 1
    try:
        dump = read_dump(args.backup)
    except ValueError as exc:
        print(exc)
        return 1
    if dump.database and dump.database != settings.db_name:
        print(f"This backup is of database '{dump.database}', not the configured '{settings.db_name}'. Nothing done.")
        return 1
    if "alembic_version" not in dump.tables:
        print("This backup has no alembic_version table; it is not a complete VisoNarc backup. Nothing done.")
        return 1

    tables, revision = current_state()
    extra = sorted(set(tables) - set(dump.tables))
    print(f"Target database : {settings.db_name} on {settings.db_host}:{settings.db_port}")
    print(f"Backup file     : {args.backup} ({args.backup.stat().st_size:,} bytes)")
    print(f"Tables replaced : {len(dump.tables)} ({', '.join(dump.tables)})")
    print(f"Migration       : current {revision or '-'} -> backup {dump.revision or '-'}")
    if extra:
        print(f"Tables dropped  : {', '.join(extra)} (not in the backup; kept in the pre-restore backup)")
    if dump.revision != revision:
        print("Note: after restoring, run `python -m alembic upgrade head` to bring the schema up to date.")
    if not args.apply:
        print("Dry run only. Add --apply to restore.")
        return 0

    exe = shutil.which("mysql") or (str(DEFAULT_MYSQL) if DEFAULT_MYSQL.exists() else None)
    if not exe:
        print("mysql client not found. Add MySQL Server 8.0\\bin to PATH.")
        return 1
    typed = input(f"This replaces the data in '{settings.db_name}'. Type the database name to continue: ")
    if typed.strip() != settings.db_name:
        print("Name did not match. Nothing was restored.")
        return 1

    print("Backing up the current database first ...")
    if backup_db.main() != 0:
        print("Pre-restore backup failed. Nothing was restored.")
        return 1

    if any(not SAFE_NAME.match(t) for t in extra):
        print("Unexpected table name in the database. Nothing was restored.")
        return 1
    # Drop tables the backup does not contain, then load the backup, in one client session.
    prefix = "SET FOREIGN_KEY_CHECKS=0;\n" + "".join(f"DROP TABLE IF EXISTS `{t}`;\n" for t in extra)
    script = prefix.encode() + TABLE_LOCKS.sub(b"", args.backup.read_bytes()) + b"\nSET FOREIGN_KEY_CHECKS=1;\n"
    with backup_db.client_option_file(settings) as cnf:
        result = subprocess.run(
            [exe, f"--defaults-extra-file={cnf}", settings.db_name], input=script, stderr=subprocess.PIPE
        )
    if result.returncode != 0:
        print("Restore failed:", result.stderr.decode(errors="replace").strip())
        print("The database may now be partly restored (MySQL cannot roll back table changes).")
        print("Restore the pre-restore backup written above the same way to return to the previous state.")
        return 1
    _, revision = current_state()
    print(f"Restore complete. Migration revision is now {revision}. Check with: python -m scripts.verify_db")
    return 0


if __name__ == "__main__":
    sys.exit(main())
