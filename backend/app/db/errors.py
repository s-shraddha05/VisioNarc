"""Safe, actionable messages for database connection failures."""

from sqlalchemy.exc import OperationalError

DB_UNAVAILABLE = "Database unavailable. Check that MySQL is running."
# MySQL client/server error codes -> messages that name the setting to check, never its value.
DB_ERROR_DETAILS = {
    1045: "The database refused the sign-in. Check DB_USER and DB_PASSWORD in backend\\.env, "
    "or re-run scripts\\setup_mysql.ps1.",
    1044: "The database user has no access to the configured database. Check DB_NAME in backend\\.env, "
    "or re-run scripts\\setup_mysql.ps1.",
    1049: "The configured database does not exist. Check DB_NAME in backend\\.env, "
    "or re-run scripts\\setup_mysql.ps1.",
}


def mysql_error_code(exc: OperationalError) -> int | None:
    args = getattr(exc.orig, "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def database_error_detail(code: int | None) -> str:
    # 2002/2003/2006/2013 (server down or connection lost) and non-MySQL errors keep the generic message.
    return DB_ERROR_DETAILS.get(code, DB_UNAVAILABLE)
