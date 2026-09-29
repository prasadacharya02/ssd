import hashlib
import os
from pathlib import Path
import random
import tempfile
import unittest

from victim_server.create_fake_files import create_all_files, restore_all_files


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class FixtureGenerationTests(unittest.TestCase):
    def test_generator_creates_clean_fixture_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "victim"
            summary = create_all_files(root, clean=True, quiet=True)
            files = [path for path in root.rglob("*") if path.is_file()]

            self.assertEqual(summary["files_created"], 18)
            self.assertEqual(len(files), 18)
            self.assertEqual(
                {path.name for path in root.iterdir()},
                {"Documents", "Downloads", "Desktop", "Pictures"},
            )
            self.assertFalse(any(path.suffix.lower() == ".wncry" for path in files))
            self.assertFalse(any("read_me" in path.name.lower() for path in files))

    def test_same_seed_produces_identical_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            create_all_files(first, seed=42, clean=True, quiet=True)
            create_all_files(second, seed=42, clean=True, quiet=True)
            self.assertEqual(tree_hashes(first), tree_hashes(second))

    def test_generator_does_not_change_global_random_state(self):
        with tempfile.TemporaryDirectory() as directory:
            random.seed(99)
            expected = random.random()
            random.seed(99)
            create_all_files(Path(directory) / "victim", quiet=True)
            actual = random.random()
            self.assertEqual(actual, expected)

    def test_restore_removes_stale_attack_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "victim"
            root.mkdir()
            stale = root / "stale.WNCRY"
            stale.write_bytes(os.urandom(64))

            restore_all_files(root, quiet=True)

            self.assertFalse(stale.exists())
            self.assertEqual(len(tree_hashes(root)), 18)


if __name__ == "__main__":
    unittest.main()
