"""Verify the configured database: connection, server version, charset, migrations and tables.

Usage (from backend/, venv active):
    python -m scripts.verify_db
Exit code 0 = all checks passed.
"""

import sys

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

import app.models  # noqa: F401 - registers all tables
from app.api.routes.health import migration_head
from app.db.base import Base
from app.db.session import get_engine


def main() -> int:
    failures = 0

    def check(ok: bool, label: str, detail: str = "") -> None:
        nonlocal failures
        failures += 0 if ok else 1
        print(f"[{'OK' if ok else 'FAIL':<4}] {label}{': ' + detail if detail else ''}")

    engine = get_engine()
    try:
        with engine.connect() as conn:
            check(True, "Connection", f"{engine.dialect.name} as {engine.url.username or '-'}")
            if engine.dialect.name == "mysql":
                version = conn.execute(text("SELECT VERSION()")).scalar_one()
                check(str(version).startswith("8."), "MySQL server version", str(version))
                db_name, charset = conn.execute(
                    text("SELECT DATABASE(), @@character_set_database")
                ).one()
                check(charset == "utf8mb4", "Database charset", f"{db_name} / {charset}")

            existing = set(inspect(conn).get_table_names())
            expected = set(Base.metadata.tables)
            missing = sorted(expected - existing)
            check(not missing, "Tables", "missing: " + ", ".join(missing) if missing else f"{len(expected)} present")

            current = None
            if "alembic_version" in existing:
                current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            head = migration_head()
            check(current == head, "Migrations", f"current={current} head={head}")

            if "admins" in existing:
                count = conn.execute(text("SELECT COUNT(*) FROM admins")).scalar_one()
                check(True, "Administrators", f"{count} account(s)")
                if count == 0:
                    print("       Create one with: python -m scripts.create_admin --username admin")
    except SQLAlchemyError as exc:
        check(False, "Connection", f"{exc.__class__.__name__}: {exc.orig if hasattr(exc, 'orig') else exc}")

    print("All database checks passed." if failures == 0 else f"{failures} check(s) failed.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
