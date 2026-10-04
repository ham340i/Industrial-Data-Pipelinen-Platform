"""Local workspace configuration contracts (issue #4)."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WorkspaceTests(unittest.TestCase):
    def test_safe_ports_and_private_persistent_storage(self):
        config = json.loads((ROOT / 'compose.yml').read_text())
        for service in config['services'].values():
            self.assertTrue(all(port.startswith('127.0.0.1:') for port in service['ports']))
            self.assertNotIn('privileged', service)
            self.assertNotIn('env_file', service)
        self.assertEqual(config['services']['api']['volumes'], ['metadata:/var/lib/lps'])
        self.assertIn('metadata', config['volumes'])
        self.assertEqual(config['services']['frontend']['depends_on']['api']['condition'], 'service_healthy')

    def test_example_has_only_public_port_defaults(self):
        settings = dict(line.split('=', 1) for line in (ROOT / '.env.example').read_text().splitlines()
                        if line and not line.startswith('#'))
        self.assertEqual(settings, {'FRONTEND_PORT': '3000', 'API_PORT': '8000'})


if __name__ == '__main__':
    unittest.main()
