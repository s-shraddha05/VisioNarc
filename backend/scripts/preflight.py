"""Check backend configuration before the server starts; called by scripts\\run_backend.ps1.

Usage (from backend/, venv active):
    python -m scripts.preflight
Exit code 0 = the server can start (a database warning does not block it).
Messages name the setting to fix but never print its value.
"""

import os
import sys

from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings

BAD_DATABASE_URL = "DATABASE_URL is not a valid database URL."


def load_settings(**overrides) -> tuple[Settings | None, list[str]]:
    """Return (settings, problems). Problems are one line each, without the offending values."""
    try:
        settings = Settings(**overrides)
    except ValidationError as exc:
        problems = []
        for err in exc.errors():
            name = str(err["loc"][0]).upper() if err["loc"] else "configuration"
            # Environment variables override backend\.env, so say where the bad value came from.
            where = "set as an environment variable" if name in os.environ else "in backend\\.env"
            problems.append(f"{name} {where} is invalid: {err['msg']}.")
        return None, problems
    try:
        settings.validate_for_startup()
    except RuntimeError as exc:
        return None, [str(exc)]
    return settings, []


def database_warning(settings: Settings) -> str | None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    from app.db.errors import database_error_detail, mysql_error_code

    connect_args = {"connect_timeout": 5} if not settings.database_url else {}
    try:
        engine = create_engine(settings.sqlalchemy_url, connect_args=connect_args, hide_parameters=True)
    except Exception:  # e.g. a malformed DATABASE_URL; its text may contain the password
        return BAD_DATABASE_URL
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        return database_error_detail(mysql_error_code(exc))
    except Exception as exc:  # driver or URL problems: report the type only, never the message
        return f"The database check failed ({exc.__class__.__name__})."
    finally:
        engine.dispose()
    return None


def main() -> int:
    if not (BACKEND_DIR / ".env").is_file():
        print("[FAIL] backend\\.env is missing. Run scripts\\bootstrap.ps1 to create it.")
        return 1
    settings, problems = load_settings()
    for problem in problems:
        print(f"[FAIL] {problem}")
    if settings is None:
        return 1
    print("[OK]   Configuration is valid.")
    warning = database_warning(settings)
    if warning == BAD_DATABASE_URL:
        print(f"[FAIL] {warning}")
        return 1
    if warning:
        print(f"[WARN] {warning} The API will start but answer 503 until this is fixed.")
    else:
        print("[OK]   Database connection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
