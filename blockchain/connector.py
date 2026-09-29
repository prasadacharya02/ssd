# blockchain/connector.py
# ============================================================
# ENTROPY - Blockchain Connector
#
# Handles all Web3 communication with Ganache and the
# ThreatLogger smart contract.
#
# Features:
# - Non-blocking event logging (background thread)
# - Auto-reconnection on connection drop
# - Detailed error reporting
#
# FALLBACK MODE:
# If Ganache is not reachable (e.g. running a demo on a machine
# without a local Ethereum node) and config.BLOCKCHAIN_FALLBACK
# is enabled, the connector transparently falls back to a local
# SQLite ledger. This keeps the dashboard fully functional and
# lets the "on-chain" ledger be demonstrated without external
# infrastructure. The fallback is clearly labelled so it is never
# mistaken for a real public chain.
# ============================================================

import json
import os
import sqlite3
import sys
import time
import logging
import threading
from datetime import datetime
from queue import Queue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

log = logging.getLogger("Blockchain")


class LocalLedger:
    """
    Lightweight, self-contained replacement for a live smart contract.

    Used when Ganache is unavailable. Stores the exact same fields a
    real ThreatLogger event would contain, so the rest of the system
    (dashboard, alerts, DQN feedback) behaves identically.
    """

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT,
                threatType  TEXT,
                timestamp   INTEGER,
                pid         INTEGER,
                entropy     INTEGER,
                processName TEXT,
                filePath    TEXT,
                actionTaken TEXT,
                status      TEXT
            )
        """)
        self.conn.commit()
        self._seq = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM ledger"
        ).fetchone()[0]
        self._lock = threading.Lock()
        log.info("[BLOCKCHAIN] Local fallback ledger ready")

    def add(self, event: dict) -> int:
        with self._lock:
            self._seq += 1
            self.conn.execute(
                """
                INSERT INTO ledger
                (id, fingerprint, threatType, timestamp, pid, entropy,
                 processName, filePath, actionTaken, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    self._seq,
                    str(event.get("fingerprint", "unknown"))[:64],
                    str(event.get("threat_type", "ransomware")),
                    int(time.time()),
                    int(event.get("pid", 0)),
                    int(float(event.get("entropy", 0)) * 100),
                    str(event.get("process", "unknown"))[:100],
                    str(event.get("file_path", ""))[:200],
                    str(event.get("action", "0")),
                    str(event.get("status", "unknown")),
                ),
            )
            self.conn.commit()
            return self._seq

    def count(self) -> int:
        with self._lock:
            return self.conn.execute(
                "SELECT COUNT(*) FROM ledger"
            ).fetchone()[0]

    def all(self) -> list:
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, fingerprint, threatType, timestamp, pid, "
                "entropy, processName, filePath, actionTaken, status "
                "FROM ledger ORDER BY id ASC"
            ).fetchall()
        return [
            {
                "id"          : r[0],
                "fingerprint" : r[1],
                "threatType"  : r[2],
                "timestamp"   : r[3],
                "pid"         : r[4],
                "entropy"     : (r[5] or 0) / 100,
                "processName" : r[6],
                "filePath"    : r[7],
                "actionTaken" : r[8],
                "status"      : r[9],
            }
            for r in rows
        ]


class BlockchainConnector:
    """
    Connects Python backend to Ganache + Solidity smart contract,
    with a transparent local-ledger fallback.

    Usage:
        bc = BlockchainConnector()
        bc.log_event({...})           # non-blocking
        events = bc.get_all_events()   # blocking read
    """

    def __init__(self):
        self.w3            = None
        self.contract      = None
        self.account       = None
        self.abi           = None
        self.last_connect  = 0
        self.connect_retry = 30   # seconds between reconnect attempts
        self.mode          = "none"   # 'ganache' | 'fallback' | 'none'
        self.fallback      = None
        self._write_queue   = Queue()
        self._worker       = None
        self._connect()
        self._worker = threading.Thread(
            target=self._write_worker,
            name="BlockchainWriter",
            daemon=True,
        )
        self._worker.start()

    # ═════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═════════════════════════════════════════════════

    def _connect(self):
        """Establish connection to Ganache; fall back to local ledger."""
        if self._try_ganache():
            return

        if config.BLOCKCHAIN_FALLBACK:
            try:
                ledger_path = os.path.join(
                    config.BLOCKCHAIN_DIR, "ledger.db"
                )
                self.fallback = LocalLedger(ledger_path)
                self.mode = "fallback"
                print("[BLOCKCHAIN] Ganache unreachable — "
                      "using LOCAL LEDGER fallback ✅")
                log.info("Ganache unreachable; using local ledger fallback")
                return
            except Exception as e:
                print(f"[BLOCKCHAIN] ❌ Fallback ledger failed: {e}")

        self.mode = "none"
        print("[BLOCKCHAIN] ❌ No blockchain connection "
              "(Ganache offline, fallback disabled)")
        log.error("No blockchain connection available")

    def _try_ganache(self) -> bool:
        """Attempt to connect to Ganache and load the contract."""
        try:
            from web3 import Web3
            self.w3 = Web3(Web3.HTTPProvider(config.GANACHE_URL))

            if self.w3.is_connected():
                print("[BLOCKCHAIN] Connected to Ganache ✅")
                log.info("Connected to Ganache")
                if self._load_contract():
                    self.mode = "ganache"
                    self.last_connect = time.time()
                    return True
        except Exception as e:
            print(f"[BLOCKCHAIN] ❌ Ganache not reachable: {e}")
            log.error(f"Ganache not reachable: {e}")
        return False

    def _reconnect_if_needed(self):
        """Try to reconnect if we lost connection (Ganache mode only)."""
        if self.mode == "ganache":
            return True

        # Rate-limit reconnect attempts
        if time.time() - self.last_connect < self.connect_retry:
            return False

        self.last_connect = time.time()
        if self._try_ganache():
            return True

        # Re-establish fallback if it dropped
        if config.BLOCKCHAIN_FALLBACK and self.fallback is None:
            try:
                ledger_path = os.path.join(
                    config.BLOCKCHAIN_DIR, "ledger.db"
                )
                self.fallback = LocalLedger(ledger_path)
                self.mode = "fallback"
                return True
            except Exception:
                pass
        return self.mode != "none"

    def _load_contract(self):
        """Load the ThreatLogger contract using ABI file."""
        abi_path = os.path.join(
            config.BASE_DIR, "blockchain", "contract_abi.json"
        )

        if not os.path.exists(abi_path):
            print(f"[BLOCKCHAIN] ❌ No ABI at: {abi_path}")
            log.error(f"ABI file missing: {abi_path}")
            return False

        try:
            with open(abi_path) as f:
                self.abi = json.load(f)

            self.contract = self.w3.eth.contract(
                address=config.CONTRACT_ADDRESS,
                abi=self.abi
            )

            accounts = self.w3.eth.accounts
            if not accounts:
                print("[BLOCKCHAIN] ❌ No accounts in Ganache")
                log.error("No accounts available")
                return False

            configured = (config.WALLET_ADDRESS or "").strip()
            if configured:
                checksum = self.w3.to_checksum_address(configured)
                if checksum not in accounts:
                    print("[BLOCKCHAIN] ❌ ENTROPY_WALLET_ADDRESS is not a Ganache account")
                    return False
                self.account = checksum
            else:
                self.account = accounts[config.ACCOUNT_INDEX]

            print(f"[BLOCKCHAIN] Contract loaded ✅")
            print(f"             Address : {config.CONTRACT_ADDRESS}")
            print(f"             Account : {self.account}")
            log.info(f"Contract loaded at {config.CONTRACT_ADDRESS}")
            return True

        except Exception as e:
            print(f"[BLOCKCHAIN] ❌ Contract load failed: {e}")
            log.error(f"Contract load failed: {e}")
            return False

    # ═════════════════════════════════════════════════
    # WRITE — LOG EVENT
    # ═════════════════════════════════════════════════

    def log_event(self, event: dict):
        """Queue an event for serialized, reliable background writing.

        A single writer prevents Ganache nonce collisions when many files are
        detected at once. The queue can be drained with :meth:`flush` during
        an orderly shutdown.
        """
        self._write_queue.put(dict(event))

    def _write_worker(self):
        while True:
            event = self._write_queue.get()
            try:
                if event is None:
                    return
                self._log_event_dispatch(event)
            except Exception as exc:
                log.error("Blockchain writer failed: %s", exc)
            finally:
                self._write_queue.task_done()

    def flush(self, timeout: float = 10.0) -> bool:
        """Wait for queued writes to finish during graceful shutdown."""
        deadline = time.time() + max(0.0, timeout)
        while self._write_queue.unfinished_tasks:
            if time.time() >= deadline:
                log.warning(
                    "Blockchain writer still has %d pending event(s)",
                    self._write_queue.unfinished_tasks,
                )
                return False
            time.sleep(0.01)
        return True

    def close(self, timeout: float = 10.0):
        """Drain pending writes and stop the writer thread."""
        drained = self.flush(timeout)
        if self._worker and self._worker.is_alive():
            self._write_queue.put(None)
            self._worker.join(timeout=max(0.0, timeout))
        return drained

    def _log_event_dispatch(self, event: dict):
        if self.mode == "ganache":
            self._log_event_sync(event)
        elif self.mode == "fallback":
            try:
                self.fallback.add(event)
                print(f"  ✅ [LEDGER] Event recorded "
                      f"| fp={str(event.get('fingerprint',''))[:12]}…")
            except Exception as e:
                print(f"  ❌ [LEDGER] Write failed: {e}")
                log.error(f"Ledger write failed: {e}")
        else:
            if not self._reconnect_if_needed():
                print("  ❌ [BLOCKCHAIN] Not connected — skipping log")
                return
            self._log_event_dispatch(event)

    def _log_event_sync(self, event: dict):
        """Actual blockchain write — runs in background (Ganache mode)."""

        if not self.contract:
            if not self._reconnect_if_needed():
                print("  ❌ [BLOCKCHAIN] Not connected — skipping log")
                return

        if not self.contract:
            print("  ❌ [BLOCKCHAIN] Contract not loaded — skipping log")
            return

        try:
            tx_hash = self.contract.functions.logThreat(
                str(event.get("fingerprint", "unknown"))[:64],
                str(event.get("threat_type", "ransomware")),
                int(event.get("pid",         0)),
                int(event.get("entropy",     0) * 100),
                str(event.get("process",     "unknown")),
                str(event.get("file_path",   ""))[:100],
                str(event.get("action",      "0")),
                str(event.get("status",      "unknown"))
            ).transact({
                "from" : self.account,
                "gas"  : 500000
            })

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"  ✅ [BLOCKCHAIN] TX Block #{receipt.blockNumber} "
                  f"| Gas: {receipt.gasUsed}")
            log.info(f"TX confirmed: block {receipt.blockNumber}")

        except ValueError as e:
            print(f"  ❌ [BLOCKCHAIN] Rejected: {e}")
            log.error(f"TX rejected: {e}")

        except ConnectionError as e:
            print(f"  ❌ [BLOCKCHAIN] Connection lost: {e}")
            log.error(f"Connection lost: {e}")
            self.contract = None   # force reconnect on next call

        except Exception as e:
            print(f"  ❌ [BLOCKCHAIN] Failed: {e}")
            log.error(f"Log failed: {e}")

    # ═════════════════════════════════════════════════
    # READ — GET EVENTS
    # ═════════════════════════════════════════════════

    def get_all_events(self):
        """Read all events from the active ledger / contract."""
        if self.mode == "fallback":
            try:
                return self.fallback.all()
            except Exception as e:
                log.error(f"Ledger read failed: {e}")
                return []

        if self.mode != "ganache":
            self._reconnect_if_needed()
            if self.mode != "ganache":
                return []

        try:
            count = self.contract.functions.getEventCount().call()
            events = []

            for i in range(count):
                raw = self.contract.functions.getEvent(i).call()
                events.append({
                    "id"          : raw[0],
                    "fingerprint" : raw[1],
                    "threatType"  : raw[2],
                    "timestamp"   : raw[3],
                    "pid"         : raw[4],
                    "entropy"     : raw[5] / 100,
                    "processName" : raw[6],
                    "filePath"    : raw[7],
                    "actionTaken" : raw[8],
                    "status"      : raw[9]
                })

            return events

        except Exception as e:
            print(f"[BLOCKCHAIN] ❌ Read failed: {e}")
            log.error(f"Read failed: {e}")
            return []

    def get_event_count(self):
        """Get total number of events in ledger."""
        if self.mode == "fallback":
            try:
                return self.fallback.count()
            except Exception:
                return 0

        if self.mode != "ganache":
            self._reconnect_if_needed()
            if self.mode != "ganache":
                return 0

        try:
            return self.contract.functions.getEventCount().call()
        except Exception as e:
            log.debug(f"Count failed: {e}")
            return 0

    # ═════════════════════════════════════════════════
    # STATUS
    # ═════════════════════════════════════════════════

    def verify_chain(self):
        """Return True only for an actual Ganache connection."""
        if self.mode != "ganache":
            return False
        try:
            return self.w3 is not None and self.w3.is_connected()
        except Exception:
            return False

    def get_status(self):
        """Get detailed status info for diagnostics."""
        return {
            "mode"           : self.mode,
            "connected"      : self.verify_chain(),
            "is_blockchain"  : self.mode == "ganache",
            "contract_loaded": self.contract is not None,
            "account"        : self.account,
            "contract_addr"  : config.CONTRACT_ADDRESS if self.contract else None,
            "network_url"    : config.GANACHE_URL,
        }