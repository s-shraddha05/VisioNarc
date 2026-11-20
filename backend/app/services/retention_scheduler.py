"""Optional automatic retention purge: once at startup, then every RETENTION_PURGE_INTERVAL_HOURS.

Enabled only when RETENTION_AUTO_PURGE=true. Logs counts only (no names or reference codes).
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.services import retention_service

logger = logging.getLogger("visonarc.retention")


class RetentionScheduler:
    def __init__(self, session_factory: Callable[[], Session], interval_hours: int):
        self.session_factory = session_factory
        self.interval_seconds = interval_hours * 3600
        self.last_run: dict | None = None
        self._task: asyncio.Task | None = None

    def run_once(self) -> dict:
        started = datetime.now(UTC)
        try:
            with self.session_factory() as db:
                deleted = retention_service.purge(db, trigger="automatic")
            self.last_run = {"at": started.isoformat(), "deleted": len(deleted), "error": None}
            logger.info("Automatic retention purge removed %d session(s).", len(deleted))
        except Exception as exc:  # noqa: BLE001 - a failed run must not stop the API
            self.last_run = {"at": started.isoformat(), "deleted": 0, "error": exc.__class__.__name__}
            logger.error("Automatic retention purge failed: %s", exc.__class__.__name__)
        return self.last_run

    async def _loop(self) -> None:
        while True:
            await run_in_threadpool(self.run_once)
            await asyncio.sleep(self.interval_seconds)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
