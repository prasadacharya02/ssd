"""Smoke tests for the standalone, read-only endpoint workspace."""
import unittest
from victim_server.app import app, VAULT_USER, VAULT_PIN


class VictimFrontendTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_workspace_and_stylesheet_are_served(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'This PC', page.data)
        self.assertIn(b'/static/explorer/assets/', page.data)
        import re
        stylesheet = re.search(rb'href="([^"]+\.css)"', page.data).group(1).decode()
        css = self.client.get(stylesheet)
        self.assertEqual(css.status_code, 200)
        self.assertIn(b'@media', css.data)

    def test_folders_remain_neutral(self):
        folders = self.client.get('/api/folders').get_json()
        self.assertEqual(len(folders), 5)
        self.assertTrue(next(f for f in folders if f['name'] == 'Quarantine')['locked'])
        for folder in folders:
            self.assertNotIn('encrypted_count', folder)

    def test_vault_stays_authenticated(self):
        self.assertEqual(self.client.get('/api/files/Quarantine').status_code, 401)
        response = self.client.post('/api/vault/login', json={'username': VAULT_USER, 'pin': VAULT_PIN})
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(self.client.get('/api/files/Quarantine').status_code, 200)
        self.client.post('/api/vault/logout')
        self.assertEqual(self.client.get('/api/files/Quarantine').status_code, 401)
