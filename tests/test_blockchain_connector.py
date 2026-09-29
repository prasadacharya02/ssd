from pathlib import Path
import tempfile
import unittest
from unittest import mock

from blockchain.connector import BlockchainConnector


class BlockchainConnectorTests(unittest.TestCase):
    def test_fallback_is_not_reported_as_a_blockchain_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch("blockchain.connector.config.BLOCKCHAIN_DIR", directory), \
                 mock.patch("blockchain.connector.config.BLOCKCHAIN_FALLBACK", True):
                connector = BlockchainConnector()
                try:
                    self.assertEqual(connector.mode, "fallback")
                    self.assertFalse(connector.verify_chain())
                    self.assertFalse(connector.get_status()["is_blockchain"])
                finally:
                    connector.close()

    def test_queued_events_are_flushed_to_fallback_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch("blockchain.connector.config.BLOCKCHAIN_DIR", directory), \
                 mock.patch("blockchain.connector.config.BLOCKCHAIN_FALLBACK", True):
                connector = BlockchainConnector()
                try:
                    connector.log_event({
                        "fingerprint": "a" * 64,
                        "entropy": 8.0,
                        "pid": 123,
                        "process": "demo",
                        "file_path": "/controlled/file.txt",
                        "action": "QUARANTINE",
                        "status": "recorded",
                    })
                    self.assertTrue(connector.flush(timeout=2.0))
                    self.assertEqual(connector.get_event_count(), 1)
                finally:
                    connector.close()


if __name__ == "__main__":
    unittest.main()
