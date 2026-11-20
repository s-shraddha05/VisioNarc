"""Create a VisoNarc administrator. The password is typed at a hidden prompt, never passed as an argument.

Usage (from backend/, venv active):
    python -m scripts.create_admin --username admin --full-name "Project Admin"
"""

import argparse
import getpass
import sys

from app.core.config import get_settings
from app.core.security import validate_password_strength
from app.db.session import get_sessionmaker
from app.services.auth_service import AuthError, create_admin


def prompt_new_password() -> str:
    while True:
        password = getpass.getpass("New password: ")
        errors = validate_password_strength(password)
        if errors:
            print("\n".join(f"  - {e}" for e in errors))
            continue
        if getpass.getpass("Repeat password: ") != password:
            print("  - Passwords do not match.")
            continue
        return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a VisoNarc administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()

    settings = get_settings()
    password = prompt_new_password()
    with get_sessionmaker()() as db:
        try:
            admin = create_admin(db, settings, args.username, password, args.full_name)
        except AuthError as exc:
            details = exc.detail if isinstance(exc.detail, list) else [exc.detail]
            print("Could not create administrator:\n" + "\n".join(f"  - {d}" for d in details))
            return 1
    print(f"Administrator '{admin.username}' created (id={admin.id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
