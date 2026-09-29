"""Small, thread-safe watchdog event de-duplicator."""

from __future__ import annotations

import time
from threading import Lock


class EventDeduplicator:
    """Suppress identical filesystem notifications in a short time window."""

    def __init__(self, window_seconds: float = 0.25):
        if window_seconds < 0:
            raise ValueError("window_seconds must be non-negative")
        self.window_seconds = window_seconds
        self._recent: dict[tuple, float] = {}
        self._lock = Lock()

    def is_duplicate(self, event: dict, now: float | None = None) -> bool:
        """Return whether this event repeats a recent identical notification."""
        current = time.monotonic() if now is None else now
        key = (
            event.get("event_type"),
            event.get("file_path"),
            event.get("dest_path"),
        )
        with self._lock:
            cutoff = current - self.window_seconds
            self._recent = {
                stored_key: timestamp
                for stored_key, timestamp in self._recent.items()
                if timestamp >= cutoff
            }
            previous = self._recent.get(key)
            self._recent[key] = current
            return previous is not None and current - previous <= self.window_seconds

    def clear(self) -> None:
        with self._lock:
            self._recent.clear()
