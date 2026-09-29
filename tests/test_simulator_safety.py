from pathlib import Path
import tempfile
import unittest
from unittest import mock

from attacker_server import ransomware_engines as engines


class SimulatorSafetyTests(unittest.TestCase):
    def test_confined_path_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "victim"
            root.mkdir()
            with mock.patch.object(engines, "_VICTIM_ROOT", root.resolve()):
                self.assertIsNone(engines._confined_path(root / ".." / "outside.txt"))
                self.assertIsNotNone(engines._confined_path(root / "Documents"))

    def test_confined_path_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "victim"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            link = root / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with mock.patch.object(engines, "_VICTIM_ROOT", root.resolve()):
                self.assertIsNone(engines._confined_path(link / "file.txt"))

    def test_encrypt_file_refuses_path_outside_victim_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "victim"
            root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("must remain unchanged", encoding="utf-8")

            with mock.patch.object(engines, "_VICTIM_ROOT", root.resolve()):
                engine = engines.BaseRansomware()
                self.assertFalse(engine.encrypt_file(outside))

            self.assertEqual(
                outside.read_text(encoding="utf-8"),
                "must remain unchanged",
            )


if __name__ == "__main__":
    unittest.main()
