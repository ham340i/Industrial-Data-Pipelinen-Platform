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


WRITE_MARKER = (
    "import os\nfrom pathlib import Path\n"
    "from app.config import settings\n"
    "from app.metadata.database import Database\n"
    "from app.metadata.models import Project\n"
    "if os.getuid() == 0:\n    raise RuntimeError('API must be non-root')\n"
    "if settings.metadata_path != Path('/var/lib/lps/metadata.sqlite3'):\n"
    "    raise RuntimeError('API metadata path does not use the volume')\n"
    "if settings.workspace_root != Path('/var/lib/lps/workspace'):\n"
    "    raise RuntimeError('API workspace path does not use the volume')\n"
    "database = Database(settings.metadata_path)\n"
    "try:\n"
    "    with database.transaction() as session:\n"
    "        session.add(Project(id='{marker}', name='Synthetic smoke'))\n"
    "finally:\n    database.close()"
)
READ_MARKER = (
    "from app.config import settings\n"
    "from app.metadata.database import Database\n"
    "from app.metadata.models import Project\n"
    "database = Database(settings.metadata_path)\n"
    "try:\n"
    "    with database.transaction() as session:\n"
    "        project = session.get(Project, '{marker}')\n"
    "        if project is None or project.name != 'Synthetic smoke':\n"
    "            raise RuntimeError('Persisted project is missing')\n"
    "        print(project.id)\n"
    "finally:\n    database.close()"
)


def get(url):
    with urlopen(url, timeout=10) as response:
        return response.read().decode()


def verify_health(url):
    health = json.loads(get(url))
    if health.get('status') != 'ok' or health.get('service') != 'local-pipeline-studio':
        raise RuntimeError('Unexpected real API health response')


class Stack:
    """One isolated Compose project on loopback ports chosen by Docker."""

    def __init__(self):
        self.project = 'lps-smoke-' + uuid4().hex[:12]
        self.env = dict(os.environ, API_PORT='0', FRONTEND_PORT='0')
        self.command = ['docker', 'compose', '--project-name', self.project,
                        '--file', str(ROOT / 'compose.yml')]

    def compose(self, *arguments):
        try:
            return subprocess.check_output([*self.command, *arguments], cwd=ROOT,
                                           env=self.env, text=True)
        except subprocess.CalledProcessError as error:
            print(error.output)
            raise

    def address(self, service, port):
        binding = self.compose('port', service, str(port)).strip()
        if not binding.startswith('127.0.0.1:'):
            raise RuntimeError('Service was not bound to loopback')
        port = int(binding.removeprefix('127.0.0.1:'))
        if not 1 <= port <= 65535:
            raise RuntimeError('Invalid published port')
        # Synthetic local smoke traffic never leaves loopback.
        return f'http://127.0.0.1:{port}'

    def up(self, *extra):
        self.compose('up', *extra, '--detach', '--wait', '--wait-timeout', '120')

    def tear_down(self):
        self.compose('down', '--volumes', '--remove-orphans', '--timeout', '10')
        if self.compose('ps', '--all', '--quiet').strip():
            raise RuntimeError('Smoke containers remain after teardown')
        print('Isolated smoke stack and synthetic metadata volume removed.')


def check_frontend(stack, frontend):
    html = get(frontend + '/')
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    if not assets or 'id="root"' not in html:
        raise RuntimeError('Built React entry point/assets missing')
    for asset in assets:
        get(frontend + asset)
    if get(frontend + '/builder') != html:
        raise RuntimeError('SPA deep link failed')
    if stack.compose('exec', '-T', 'frontend', 'id', '-u').strip() == '0':
        raise RuntimeError('Frontend must run as a non-root user')


def check_persistence(stack, marker):
    """Recreate the containers and require the marker project to survive."""
    stack.compose('down', '--timeout', '10')
    stack.up()
    saved = stack.compose('exec', '-T', 'api', 'python', '-c',
                          READ_MARKER.format(marker=marker))
    if saved.strip() != marker:
        raise RuntimeError('Metadata did not survive container recreation')
    frontend = stack.address('frontend', 8080)
    verify_health(frontend + HEALTH_PATH)
    project = json.loads(get(frontend + '/api/v1/projects/' + marker))
    if project.get('id') != marker or project.get('name') != 'Synthetic smoke':
        raise RuntimeError('Project API did not reopen persisted metadata')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true', help='Also run installed Playwright/Chromium against the real stack')
    args = parser.parse_args()
    stack = Stack()
    try:
        stack.up('--build')
        frontend = stack.address('frontend', 8080)
        verify_health(stack.address('api', 8000) + HEALTH_PATH)
        verify_health(frontend + HEALTH_PATH)
        check_frontend(stack, frontend)
        marker = str(uuid4())
        stack.compose('exec', '-T', 'api', 'python', '-c', WRITE_MARKER.format(marker=marker))
        if args.browser:
            subprocess.run(['npm', 'exec', '--', 'playwright', 'test', '--config', 'playwright.compose.config.ts'],
                           cwd=ROOT / 'frontend', env=dict(stack.env, COMPOSE_BASE_URL=frontend), check=True)
        check_persistence(stack, marker)
        print('PASS: real API, frontend assets, SPA routes, proxy, non-root SQLite writes and project persistence.')
    finally:
        stack.tear_down()


if __name__ == '__main__':
    main()
