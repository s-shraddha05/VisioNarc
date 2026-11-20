"""List or delete analysis sessions whose retain_until date has passed.

Usage (from backend/, venv active):
    python -m scripts.purge_expired            # dry run: list what would be deleted (default)
    python -m scripts.purge_expired --apply    # delete after typing PURGE
    python -m scripts.purge_expired --apply --yes   # non-interactive (e.g. Task Scheduler)

Back up first: python -m scripts.backup_db. Deleted sessions can only be recovered from a backup.
"""

import argparse
import sys

from app.db.session import get_sessionmaker
from app.services import retention_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge expired VisoNarc analysis sessions")
    parser.add_argument("--apply", action="store_true", help="actually delete (default is a dry run)")
    parser.add_argument("--yes", action="store_true", help="skip the interactive confirmation")
    args = parser.parse_args()

    with get_sessionmaker()() as db:
        expired = retention_service.find_expired(db)
        if not expired:
            print("No sessions are past their retention date. Nothing to do.")
            return 0
        print(f"{len(expired)} session(s) past their retention date:")
        for e in expired:
            print(
                f"  {e.reference_code}  retain_until={e.retain_until:%Y-%m-%d %H:%M} UTC  status={e.status}  "
                f"face={e.face_measurements} motion={e.motion_measurements} voice={e.voice_measurements} "
                f"combined={e.combined_records}"
            )
        if not args.apply:
            print("Dry run only. Re-run with --apply to delete them (back up first: python -m scripts.backup_db).")
            return 0
        if not args.yes and input("Type PURGE to delete these sessions permanently: ").strip() != "PURGE":
            print("Cancelled. Nothing was deleted.")
            return 1
        deleted = retention_service.purge(db, trigger="cli", only_ids={e.id for e in expired})
    print(f"Deleted {len(deleted)} session(s) and their dependent records.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
