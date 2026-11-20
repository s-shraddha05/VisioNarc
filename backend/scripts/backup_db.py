"""Back up the configured MySQL database with mysqldump before migrations.

Usage (from backend/, venv active):
    python -m scripts.backup_db
Writes backend/backups/visonarc-<timestamp>.sql (git-ignored). Credentials are passed through a
temporary option file that is deleted immediately; they are never printed or put on the command line.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings

DEFAULT_MYSQLDUMP = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe")


@contextmanager
def client_option_file(settings):
    """Yield a temporary MySQL option file with the DB_* credentials; it is deleted afterwards."""
    fd, cnf = tempfile.mkstemp(suffix=".cnf")
    try:
        password = settings.db_password.replace("\\", "\\\\").replace('"', '\\"')
        with os.fdopen(fd, "w") as f:
            f.write(f'[client]\nuser={settings.db_user}\npassword="{password}"\nhost={settings.db_host}\nport={settings.db_port}\n')
        yield cnf
    finally:
        os.remove(cnf)


def main() -> int:
    settings = get_settings()
    if settings.database_url:
        print("DATABASE_URL is set; this script only backs up the MySQL DB_* configuration.")
        return 1
    exe = shutil.which("mysqldump") or (str(DEFAULT_MYSQLDUMP) if DEFAULT_MYSQLDUMP.exists() else None)
    if not exe:
        print("mysqldump not found. Add MySQL Server 8.0\\bin to PATH.")
        return 1
    out_dir = BACKEND_DIR / "backups"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{settings.db_name}-{datetime.now(UTC):%Y%m%d-%H%M%S}.sql"

    with client_option_file(settings) as cnf, open(out, "wb") as dump:
        result = subprocess.run(
            [exe, f"--defaults-extra-file={cnf}", "--single-transaction", "--no-tablespaces", "--skip-add-locks",
             "--skip-triggers", "--routines=false", settings.db_name],
            stdout=dump, stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        out.unlink(missing_ok=True)
        print("Backup failed:", result.stderr.decode(errors="replace").strip())
        return 1
    print(f"Backup written: {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
