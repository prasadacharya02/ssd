import unittest

from monitoring.event_deduplicator import EventDeduplicator


class EventDeduplicatorTests(unittest.TestCase):
    def test_identical_events_in_window_are_suppressed(self):
        deduplicator = EventDeduplicator(window_seconds=1.0)
        event = {"event_type": "MODIFIED", "file_path": "/tmp/a.txt"}

        self.assertFalse(deduplicator.is_duplicate(event, now=10.0))
        self.assertTrue(deduplicator.is_duplicate(event, now=10.5))
        self.assertFalse(deduplicator.is_duplicate(event, now=11.6))

    def test_different_event_identity_is_not_suppressed(self):
        deduplicator = EventDeduplicator(window_seconds=1.0)
        first = {"event_type": "MODIFIED", "file_path": "/tmp/a.txt"}
        second = {"event_type": "RENAMED", "file_path": "/tmp/a.txt"}

        self.assertFalse(deduplicator.is_duplicate(first, now=1.0))
        self.assertFalse(deduplicator.is_duplicate(second, now=1.1))

    def test_rename_destination_is_part_of_identity(self):
        deduplicator = EventDeduplicator(window_seconds=1.0)
        first = {
            "event_type": "RENAMED",
            "file_path": "/tmp/a.txt",
            "dest_path": "/tmp/a.locked",
        }
        second = {
            "event_type": "RENAMED",
            "file_path": "/tmp/a.txt",
            "dest_path": "/tmp/a.other",
        }

        self.assertFalse(deduplicator.is_duplicate(first, now=1.0))
        self.assertFalse(deduplicator.is_duplicate(second, now=1.1))


if __name__ == "__main__":
    unittest.main()
