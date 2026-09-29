from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
import unittest

import main


class HealthCheckTests(unittest.TestCase):
    def test_missing_dependencies_return_failure(self):
        output = StringIO()
        with mock.patch("main.util.find_spec", return_value=None):
            with redirect_stdout(output):
                exit_code = main.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Environment incomplete", output.getvalue())
        self.assertIn("[MISSING]", output.getvalue())

    def test_complete_environment_returns_success(self):
        output = StringIO()
        with mock.patch("main.util.find_spec", return_value=object()):
            with mock.patch("main.metadata.version", return_value="1.2.3"):
                with redirect_stdout(output):
                    exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Environment ready", output.getvalue())
        self.assertNotIn("[MISSING]", output.getvalue())

    def test_missing_optional_packages_do_not_fail_healthcheck(self):
        output = StringIO()

        def find_spec(module):
            return None if module in {"torch", "web3", "eventlet", "colorama"} else object()

        with mock.patch("main.util.find_spec", side_effect=find_spec):
            with mock.patch("main.metadata.version", return_value="1.2.3"):
                with redirect_stdout(output):
                    exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("optional package(s) unavailable", output.getvalue())
        self.assertIn("[OPTIONAL]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
