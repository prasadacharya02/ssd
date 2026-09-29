"""Federated threat-fingerprint exchange.

The pitch's network effect, made concrete: when one node contains a
file as a confirmed threat, every other node can ask "have I seen this
fingerprint before?" — and answer *yes* with the provenance (who saw
it, when, how many times) instead of re-learning the same threat from
scratch.

Design notes (honest about what this is and is not):

* In a real deployment this registry is the **network** — many nodes,
  each with its own store, replicating over the shared chain. In this
  lab it is a single SQLite file that several *simulated* nodes (one
  ``FingerprintExchange`` instance per node identity) open together.
  The schema and API are identical in both worlds, so the lab
  exercises the same logic a deployment would.
* Only **confirmed threats** (files actually contained/quarantined)
  are written. An alert is a suspicion, not a shared fact.
* A fingerprint match is **corroborating evidence**, never a standalone
  detector: a single node's sighting only adds context. A fingerprint
  seen by ``config.EXCHANGE_CONFIRM_THRESHOLD`` or more *independent*
  nodes is treated as a known threat (auto-confirm). That threshold is
  the defence against a poisoned or buggy node seeding the exchange
  with a clean file's hash.
* The blockchain log stays the **tamper-evident anchor** for each
  node's own incidents; the exchange is the cross-node memory.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
import time
import uuid

import config

__all__ = ["FingerprintExchange", "default_node_id", "get_exchange"]

_MAX_SOURCES = 100
_EVIDENCE_MAX = 200

_EXCHANGE = None
_EXCHANGE_LOCK = threading.Lock()


def get_exchange() -> "FingerprintExchange":
    """The node's shared view of the exchange (lazy singleton).

    Both the live pipeline (response sharing, flag collection) and the
    benchmark harness route through here; tests and the multi-node
    simulation inject their own instances instead.
    """
    global _EXCHANGE
    if _EXCHANGE is None:
        with _EXCHANGE_LOCK:
            if _EXCHANGE is None:
                _EXCHANGE = FingerprintExchange()
    return _EXCHANGE


def default_node_id() -> str:
    """Stable, human-readable identity for this lab node.

    ``ENTROPY_NODE_ID`` wins when set (the simulation sets one per
    simulated tenant); otherwise derive a stable id from the hostname
    so the same machine always reports as the same node.
    """
    if config.EXCHANGE_NODE_ID:
        return config.EXCHANGE_NODE_ID
    return f"node-{uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname())}"


class FingerprintExchange:
    """One node's view of the shared threat-fingerprint registry."""

    def __init__(self, db_path: str | None = None, node_id: str | None = None):
        self.db_path = db_path or config.THREAT_EXCHANGE_DB
        self.node_id = node_id or default_node_id()
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # RLock: register() returns lookup() while holding the lock.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS threat_fingerprints (
                       fingerprint      TEXT PRIMARY KEY,
                       first_seen       REAL NOT NULL,
                       last_seen        REAL NOT NULL,
                       sightings        INTEGER NOT NULL DEFAULT 1,
                       sources          TEXT NOT NULL DEFAULT '[]',
                       threat_type      TEXT NOT NULL DEFAULT 'ransomware',
                       file_extension   TEXT NOT NULL DEFAULT '',
                       file_size        INTEGER NOT NULL DEFAULT 0,
                       first_evidence   TEXT NOT NULL DEFAULT '',
                       latest_reference TEXT NOT NULL DEFAULT ''
                   )"""
            )
            # WAL lets several simulated nodes read while another writes
            # inside one process (and survives a crash mid-write).
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.commit()

    # ── WRITE ──────────────────────────────────────────────

    def register(self, fingerprint: str, threat_type: str = "ransomware",
                 file_extension: str = "", file_size: int = 0,
                 evidence: str = "", reference: str = "",
                 now: float | None = None) -> dict:
        """Record this node's confirmed sighting of a fingerprint.

        Upsert: the first sighting creates the record; later sightings
        from *any* node increment ``sightings`` and add the node to
        ``sources``. Returns the record as stored.
        """
        fingerprint = (fingerprint or "").strip().lower()
        if not fingerprint:
            raise ValueError("fingerprint must be a non-empty hash")
        now = time.time() if now is None else float(now)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM threat_fingerprints WHERE fingerprint=?",
                (fingerprint,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    """INSERT INTO threat_fingerprints
                       (fingerprint, first_seen, last_seen, sightings,
                        sources, threat_type, file_extension, file_size,
                        first_evidence, latest_reference)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (fingerprint, now, now, 1, json.dumps([self.node_id]),
                     threat_type, file_extension, int(file_size or 0),
                     str(evidence or "")[:_EVIDENCE_MAX],
                     str(reference or "")),
                )
            else:
                sources = json.loads(row["sources"] or "[]")
                if self.node_id not in sources:
                    sources.append(self.node_id)
                self._conn.execute(
                    """UPDATE threat_fingerprints
                       SET last_seen=?, sightings=sightings+1, sources=?,
                           latest_reference=?
                       WHERE fingerprint=?""",
                    (now, json.dumps(sources[-_MAX_SOURCES:]),
                     str(reference or "") or row["latest_reference"],
                     fingerprint),
                )
            self._conn.commit()
            return self.lookup(fingerprint)

    # ── READ ───────────────────────────────────────────────

    def lookup(self, fingerprint: str) -> dict | None:
        """Return prior sightings of a fingerprint, or None (unknown)."""
        fingerprint = (fingerprint or "").strip().lower()
        if not fingerprint:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM threat_fingerprints WHERE fingerprint=?",
                (fingerprint,),
            ).fetchone()
        if row is None:
            return None
        rec = dict(row)
        rec["sources"] = json.loads(rec["sources"] or "[]")
        return rec

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute(
                "SELECT COUNT(*) AS c FROM threat_fingerprints"
            ).fetchone()["c"])

    def close(self):
        with self._lock:
            self._conn.close()
