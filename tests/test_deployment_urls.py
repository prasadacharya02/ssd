"""Regressions for two deployment bugs that only appear when the lab is
reached through a reverse proxy (hosted preview, port-forward, ngrok).

1. The attacker console advertised sibling links built from the BIND
   address, so it handed the browser ``http://0.0.0.0:5000`` — an address
   no client can open. Clicking through from the console therefore landed
   on a dead page and the SOC feed appeared not to react to an attack.

2. The victim vault issued a plain ``SameSite=Lax`` session cookie, which
   browsers withhold from the cross-site requests an embedded (iframe)
   view makes. The PIN was accepted and the vault still rendered empty.
"""

import unittest
from unittest import mock

from attacker_server import app as attacker_app
from victim_server.app import VAULT_PIN, VAULT_USER, app as victim_app


class _Handler:
    """Just enough of a handler for the link builder."""

    def __init__(self, host, proto=None):
        self.headers = {"Host": host}
        if proto:
            self.headers["X-Forwarded-Proto"] = proto


class SiblingLinkTests(unittest.TestCase):
    """The console must never publish an unreachable bind address."""

    def _links(self, host, proto=None):
        handler = _Handler(host, proto)
        with mock.patch.object(attacker_app.config, "PUBLIC_VICTIM_URL", ""), \
             mock.patch.object(attacker_app.config, "PUBLIC_DASHBOARD_URL", ""), \
             mock.patch.object(attacker_app.config, "PUBLIC_ATTACKER_URL", ""):
            return attacker_app._runtime_links(handler)

    def test_loopback_links_use_the_loopback_host(self):
        links = self._links("127.0.0.1:8001")
        self.assertEqual(links["__DASHBOARD_URL__"], "http://127.0.0.1:5000")
        self.assertEqual(links["__VICTIM_URL__"], "http://127.0.0.1:5001")

    def test_links_never_contain_a_wildcard_bind_address(self):
        for host in ("0.0.0.0:8001", "127.0.0.1:8001", "8001-lab.example.com"):
            for value in self._links(host).values():
                self.assertNotIn("0.0.0.0", value, f"host={host}")

    def test_port_labelled_proxy_links_are_rewritten(self):
        """``8001-preview.example`` -> ``5000-preview.example``, over https."""
        links = self._links("8001-preview.example.com", proto="https")
        self.assertEqual(links["__DASHBOARD_URL__"],
                         "https://5000-preview.example.com")
        self.assertEqual(links["__VICTIM_URL__"],
                         "https://5001-preview.example.com")
        self.assertEqual(links["__ATTACKER_URL__"],
                         "https://8001-preview.example.com")

    def test_explicit_public_url_overrides_request_host(self):
        handler = _Handler("8001-preview.example.com", proto="https")
        with mock.patch.object(attacker_app.config, "PUBLIC_DASHBOARD_URL",
                               "https://soc.internal"):
            links = attacker_app._runtime_links(handler)
        self.assertEqual(links["__DASHBOARD_URL__"], "https://soc.internal")

    def test_react_console_defers_to_the_browser(self):
        """The bundle derives its own links from window.location — more
        reliable than the Host a proxy chose to forward — so the server must
        inject nothing unless the operator set an explicit override."""
        handler = _Handler("127.0.0.1:8001")
        with mock.patch.object(attacker_app.config, "PUBLIC_VICTIM_URL", ""), \
             mock.patch.object(attacker_app.config, "PUBLIC_DASHBOARD_URL", ""):
            links = attacker_app._runtime_links(handler, client_derives=True)
        self.assertEqual(links["__VICTIM_URL__"], "")
        self.assertEqual(links["__DASHBOARD_URL__"], "")

    def test_react_console_still_honours_an_explicit_override(self):
        handler = _Handler("127.0.0.1:8001")
        with mock.patch.object(attacker_app.config, "PUBLIC_DASHBOARD_URL",
                               "https://soc.internal"):
            links = attacker_app._runtime_links(handler, client_derives=True)
        self.assertEqual(links["__DASHBOARD_URL__"], "https://soc.internal")


class VaultSessionCookieTests(unittest.TestCase):
    """The vault session must survive being embedded on another origin."""

    def _login_cookie(self, extra_headers=None):
        client = victim_app.test_client()
        response = client.post(
            "/api/vault/login",
            json={"username": VAULT_USER, "pin": VAULT_PIN},
            headers=extra_headers or {},
        )
        self.assertTrue(response.get_json()["ok"])
        raw = response.headers.get("Set-Cookie", "")
        return {part.split("=", 1)[0].strip().lower(): part.split("=", 1)[1].strip()
                for part in raw.split(";") if "=" in part}, raw

    def test_plain_http_keeps_lax_cookie(self):
        """The local 127.0.0.1 demo must keep working exactly as before:
        SameSite=None is rejected by browsers unless Secure, and Secure
        cookies are not sent over plain HTTP."""
        _, raw = self._login_cookie()
        self.assertIn("SameSite=Lax", raw)
        self.assertNotIn("Secure", raw)

    def test_https_proxy_emits_embeddable_cookie(self):
        _, raw = self._login_cookie({"X-Forwarded-Proto": "https"})
        self.assertIn("SameSite=None", raw)
        self.assertIn("Secure", raw)

    def test_vault_listing_is_reachable_after_login(self):
        """End-to-end: the PIN unlocks a listing rather than an empty view."""
        client = victim_app.test_client()
        client.post("/api/vault/login",
                    json={"username": VAULT_USER, "pin": VAULT_PIN})
        response = client.get("/api/quarantine")
        self.assertEqual(response.status_code, 200)
        self.assertIn("files", response.get_json())

    def test_vault_stays_locked_without_login(self):
        client = victim_app.test_client()
        response = client.get("/api/quarantine")
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.get_json()["auth_required"])

    def test_login_issues_a_reusable_token(self):
        client = victim_app.test_client()
        response = client.post("/api/vault/login",
                               json={"username": VAULT_USER, "pin": VAULT_PIN})
        self.assertTrue(response.get_json()["ok"])
        self.assertTrue(response.get_json()["token"])

    def test_token_alone_unlocks_the_vault_without_any_cookie(self):
        """The case that made the vault render empty behind a proxy: the
        browser holds no cookie for the origin, so the credential has to
        travel in a header instead."""
        issued = victim_app.test_client().post(
            "/api/vault/login",
            json={"username": VAULT_USER, "pin": VAULT_PIN},
        ).get_json()["token"]

        fresh = victim_app.test_client()   # never saw the Set-Cookie
        response = fresh.get("/api/quarantine",
                             headers={"X-Vault-Token": issued})
        self.assertEqual(response.status_code, 200)
        self.assertIn("files", response.get_json())
        status = fresh.get("/api/vault/status",
                           headers={"X-Vault-Token": issued}).get_json()
        self.assertTrue(status["unlocked"])
        self.assertEqual(status["user"], VAULT_USER)

    def test_tampered_or_absent_token_is_rejected(self):
        fresh = victim_app.test_client()
        self.assertEqual(
            fresh.get("/api/quarantine",
                      headers={"X-Vault-Token": "not-a-real-token"}).status_code,
            401,
        )
        self.assertEqual(fresh.get("/api/quarantine").status_code, 401)


if __name__ == "__main__":
    unittest.main()
