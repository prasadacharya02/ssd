import unittest
from unittest import mock

from attacker_server import app as attacker_app


class _Handler:
    def __init__(self, address, authorization=""):
        self.client_address = (address, 12345)
        self.headers = {"Authorization": authorization}


class ControlSecurityTests(unittest.TestCase):
    def test_controls_allow_loopback_by_default(self):
        with mock.patch.object(attacker_app.config, "CONTROL_TOKEN", ""):
            self.assertTrue(attacker_app._control_authorized(_Handler("127.0.0.1")))
            self.assertFalse(attacker_app._control_authorized(_Handler("192.0.2.10")))

    def test_remote_controls_require_bearer_token(self):
        with mock.patch.object(attacker_app.config, "CONTROL_TOKEN", "secret"):
            self.assertFalse(attacker_app._control_authorized(_Handler("192.0.2.10")))
            self.assertTrue(
                attacker_app._control_authorized(
                    _Handler("192.0.2.10", "Bearer secret")
                )
            )
            self.assertFalse(
                attacker_app._control_authorized(
                    _Handler("192.0.2.10", "Bearer wrong")
                )
            )


if __name__ == "__main__":
    unittest.main()
