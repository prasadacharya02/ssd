"""Registry of the defender's OWN filesystem actions.

The monitor watches the victim estate; the defender then writes to that
same estate (restores a clean copy, renames a file back, moves a file
into quarantine). Without this registry every one of those writes came
back through the monitor as a brand-new event and was judged like an
attack:

  * a restore (``.restore_tmp.<pid>.<ns>`` → ``Passwords.txt``) looked
    like a rename with an extension change;
  * the restored clean file showed a huge entropy "jump" relative to the
    ciphertext reading before it;
  * moving a file into quarantine produced DELETED events that looked
    like tampering with the protected store.

That feedback loop quarantined CLEAN restored files, published their
hashes as threats, and occasionally lost a file entirely. The pipeline
now consults this registry and drops those echoes.

Everything is in-process (the pipeline runner performs every response
action itself) and time-bounded, so a later, real modification of the
same file is analysed normally.
"""

from __future__ import annotations

import os
import time
from threading import Lock

# How long an action's filesystem echo is expected to keep arriving.
# Polling observers report changes up to a couple of seconds late.
ECHO_WINDOW_SECONDS = 20.0


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path or ""))


class DefenderActions:
    def __init__(self, window: float = ECHO_WINDOW_SECONDS):
        self.window = window
        self._lock = Lock()
        self._restored: dict[str, tuple[float, str]] = {}   # path -> (t, sha)
        self._moved_away: dict[str, float] = {}              # path -> t

    # ── recording ────────────────────────────────────────────
    def record_restore(self, path: str, sha256: str | None) -> None:
        if not path or not sha256:
            return
        with self._lock:
            self._restored[_norm(path)] = (time.time(), sha256)

    def record_moved_away(self, path: str) -> None:
        """The defender removed *path* (quarantine move / rename-back)."""
        if not path:
            return
        with self._lock:
            self._moved_away[_norm(path)] = time.time()

    # ── queries ──────────────────────────────────────────────
    def _prune(self, now: float) -> None:
        for d in (self._restored, self._moved_away):
            for key in [k for k, v in d.items()
                        if now - (v[0] if isinstance(v, tuple) else v)
                        > self.window]:
                del d[key]

    def is_restore_echo(self, path: str, sha256: str | None) -> bool:
        """True if *path* currently holds exactly the content the
        defender restored there moments ago."""
        if not path or not sha256:
            return False
        now = time.time()
        with self._lock:
            self._prune(now)
            entry = self._restored.get(_norm(path))
        return bool(entry and entry[1] == sha256)

    def recently_restored(self, path: str) -> bool:
        now = time.time()
        with self._lock:
            self._prune(now)
            return _norm(path) in self._restored

    def is_own_removal(self, path: str) -> bool:
        now = time.time()
        with self._lock:
            self._prune(now)
            return _norm(path) in self._moved_away

    def clear(self) -> None:
        with self._lock:
            self._restored.clear()
            self._moved_away.clear()


_registry = DefenderActions()


def get_registry() -> DefenderActions:
    return _registry
