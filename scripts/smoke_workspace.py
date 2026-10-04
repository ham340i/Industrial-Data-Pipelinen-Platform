#!/usr/bin/env python3
"""Test an isolated Compose stack; remove only its synthetic resources afterward."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HEALTH_PATH = '/api/v1/health'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true', help='Also run installed Playwright/Chromium against the real stack')
    args = parser.parse_args()
    project = 'lps-smoke-' + uuid4().hex[:12]
    env = dict(os.environ, API_PORT='0', FRONTEND_PORT='0')
    command = ['docker', 'compose', '--project-name', project, '--file', str(ROOT / 'compose.yml')]

    def compose(*arguments):
        try:
            return subprocess.check_output([*command, *arguments], cwd=ROOT, env=env, text=True)
        except subprocess.CalledProcessError as error:
            print(error.output)
            raise

    def address(service, port):
        binding = compose('port', service, str(port)).strip()
        if not binding.startswith('127.0.0.1:'):
            raise RuntimeError('Service was not bound to loopback')
        port = int(binding.removeprefix('127.0.0.1:'))
        if not 1 <= port <= 65535:
            raise RuntimeError('Invalid published port')
        # Synthetic local smoke traffic never leaves loopback.
        return f'http://127.0.0.1:{port}'

    def get(url):
        with urlopen(url, timeout=10) as response:
            return response.read().decode()

    def verify_health(url):
        health = json.loads(get(url))
        if health.get('status') != 'ok' or health.get('service') != 'local-pipeline-studio':
            raise RuntimeError('Unexpected real API health response')

    try:
        compose('up', '--build', '--detach', '--wait', '--wait-timeout', '120')
        frontend = address('frontend', 8080)
        verify_health(address('api', 8000) + HEALTH_PATH)
        verify_health(frontend + HEALTH_PATH)
        html = get(frontend + '/')
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
        if not assets or 'id="root"' not in html:
            raise RuntimeError('Built React entry point/assets missing')
        for asset in assets:
            get(frontend + asset)
        if get(frontend + '/builder') != html:
            raise RuntimeError('SPA deep link failed')
        if compose('exec', '-T', 'frontend', 'id', '-u').strip() == '0':
            raise RuntimeError('Frontend must run as a non-root user')
        marker = uuid4().hex
        compose('exec', '-T', 'api', 'python', '-c',
                "import os\nfrom pathlib import Path\n"
                "if os.getuid() == 0:\n    raise RuntimeError('API must be non-root')\n"
                f"Path('/var/lib/lps/smoke.txt').write_text('{marker}')")
        if args.browser:
            subprocess.run(['npm', 'exec', '--', 'playwright', 'test', '--config', 'playwright.compose.config.ts'],
                           cwd=ROOT / 'frontend', env=dict(env, COMPOSE_BASE_URL=frontend), check=True)
        compose('down', '--timeout', '10')
        compose('up', '--detach', '--wait', '--wait-timeout', '120')
        saved = compose('exec', '-T', 'api', 'python', '-c',
                        "from pathlib import Path; print(Path('/var/lib/lps/smoke.txt').read_text())")
        if saved.strip() != marker:
            raise RuntimeError('Metadata did not survive container recreation')
        verify_health(address('frontend', 8080) + HEALTH_PATH)
        print('PASS: real API, frontend assets, SPA routes, proxy, non-root metadata writes and persistence.')
    finally:
        compose('down', '--volumes', '--remove-orphans', '--timeout', '10')
        if compose('ps', '--all', '--quiet').strip():
            raise RuntimeError('Smoke containers remain after teardown')
        print('Isolated smoke stack and synthetic metadata volume removed.')


if __name__ == '__main__':
    main()
