from pathlib import Path
import tempfile
import unittest
from unittest import mock

from attacker_server import ransomware_engines as engines
from entropy.entropy_calculator import EntropyAnalyzer
from victim_server.create_fake_files import create_all_files


class LabIntegrationTests(unittest.TestCase):
    """Dependency-light integration coverage for the attacker/victim flow."""

    def test_fixture_attack_and_entropy_detection_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            victim_root = Path(directory) / "user_files"
            create_all_files(victim_root, seed=7, clean=True, quiet=True)
            source = next(victim_root.rglob("*.txt"))
            original = source.read_bytes()

            with mock.patch.object(engines, "_VICTIM_ROOT", victim_root.resolve()), \
                 mock.patch.object(engines, "VICTIM_BASE", str(victim_root)):
                engine = engines.WannaCryEngine()
                files, folders = engine.collect_files()
                self.assertTrue(files)
                self.assertTrue(folders)
                self.assertTrue(engine.drop_ransom_note(folders[0]))
                self.assertTrue(engine.encrypt_file(source))

            encrypted = source.with_name(source.name + engine.extension)
            self.assertFalse(source.exists())
            self.assertTrue(encrypted.exists())
            self.assertNotEqual(encrypted.read_bytes()[: len(original)], original)

            result = EntropyAnalyzer().analyze(str(encrypted))
            self.assertTrue(result["is_readable"])
            self.assertGreater(result["entropy_overall"], 7.0)
            self.assertEqual(result["file_extension"], engine.extension.lower())

    def test_attack_scan_never_returns_paths_outside_victim_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "user_files"
            root.mkdir()
            (root / "Documents").mkdir()
            inside = root / "Documents" / "safe.txt"
            inside.write_text("safe", encoding="utf-8")
            outside = Path(directory) / "outside.txt"
            outside.write_text("must not be scanned", encoding="utf-8")

            with mock.patch.object(engines, "_VICTIM_ROOT", root.resolve()), \
                 mock.patch.object(engines, "VICTIM_BASE", str(root)):
                files, _ = engines.WannaCryEngine().collect_files()

            self.assertEqual(files, [str(inside)])
            self.assertNotIn(str(outside), files)


if __name__ == "__main__":
    unittest.main()
