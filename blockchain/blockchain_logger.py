"""Legacy compatibility facade for :mod:`blockchain.connector`.

Use ``BlockchainConnector`` for all new blockchain/local-ledger operations.
This module no longer maintains a second Web3 implementation.
"""

from __future__ import annotations

import warnings

from .connector import BlockchainConnector

warnings.warn(
    "blockchain.blockchain_logger is legacy; use BlockchainConnector",
    DeprecationWarning,
    stacklevel=2,
)


class BlockchainLogger:
    """Compatibility adapter backed by the canonical connector."""

    def __init__(self):
        self.connector = BlockchainConnector()

    @property
    def connected(self):
        return self.connector.verify_chain()

    def log_threat(self, response: dict) -> dict:
        """Queue a threat in the canonical connector."""
        event = {
            "fingerprint": response.get("fingerprint", ""),
            "threat_type": response.get("threat_type", "ransomware"),
            "pid": response.get("pid", 0),
            "entropy": response.get("entropy", 0.0),
            "process": response.get("process_name", response.get("process", "unknown")),
            "file_path": response.get("file_path", ""),
            "action": response.get("ai_action_name", response.get("action", "UNKNOWN")),
            "status": response.get("status", "confirmed"),
        }
        self.connector.log_event(event)
        return {
            "success": True,
            "queued": True,
            "mode": self.connector.mode,
        }

    def get_event_count(self):
        return self.connector.get_event_count()

    def get_all_events(self):
        return self.connector.get_all_events()

    def verify_chain(self):
        return self.connector.verify_chain()

    def close(self):
        return self.connector.close()


if __name__ == "__main__":
    print("This legacy module is an adapter. Use blockchain.connector instead.")
