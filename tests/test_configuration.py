import os
from pathlib import Path
from unittest import mock
import unittest

import config


class ConfigurationTests(unittest.TestCase):
    def test_relative_paths_resolve_from_repository_root(self):
        resolved = config._resolve_path("runtime/example.db")
        self.assertEqual(Path(resolved), config.BASE_PATH / "runtime" / "example.db")

    def test_boolean_environment_values_are_strict(self):
        for raw in ("true", "YES", "1", "on"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"TEST_BOOL": raw}):
                self.assertTrue(config._env_bool("TEST_BOOL", False))

        for raw in ("false", "NO", "0", "off"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"TEST_BOOL": raw}):
                self.assertFalse(config._env_bool("TEST_BOOL", True))

        with mock.patch.dict(os.environ, {"TEST_BOOL": "sometimes"}):
            with self.assertRaises(ValueError):
                config._env_bool("TEST_BOOL", False)

    def test_numeric_settings_reject_values_below_minimum(self):
        with mock.patch.dict(os.environ, {"TEST_INT": "0"}):
            with self.assertRaises(ValueError):
                config._env_int("TEST_INT", 5, minimum=1)
        with mock.patch.dict(os.environ, {"TEST_FLOAT": "-1.5"}):
            with self.assertRaises(ValueError):
                config._env_float("TEST_FLOAT", 1.0, minimum=0.0)

    def test_default_watch_folder_is_confined_to_test_data(self):
        self.assertEqual(config.WATCH_FOLDERS, [config.TESTING_DATA_DIR])


if __name__ == "__main__":
    unittest.main()
