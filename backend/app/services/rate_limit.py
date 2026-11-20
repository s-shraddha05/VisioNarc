"""In-memory sliding-window limiter for failed sign-ins per client IP.

Keyed on the TCP peer address only (request.client.host). X-Forwarded-For and similar headers are
never trusted, because any client can set them. Limits are per backend process: running several
uvicorn workers would give each its own counter (VisoNarc runs one process locally).
"""

import threading
import time
from collections import deque


class FailureRateLimiter:
    def __init__(self, max_failures: int, window_seconds: int, clock=time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        while events and now - events[0] >= self.window:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def retry_after(self, key: str) -> int | None:
        """Seconds until another attempt is allowed, or None if allowed now."""
        with self._lock:
            now = self._clock()
            events = self._prune(key, now)
            if len(events) < self.max_failures:
                return None
            return max(1, int(self.window - (now - events[0])) + 1)

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._prune(key, now)
            self._events.setdefault(key, deque()).append(now)
