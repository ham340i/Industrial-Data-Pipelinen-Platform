#!/usr/bin/env python3
"""Validate repository configuration and run limited, path-only secret checks."""

import ast
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

from check_docs import ROOT, repository_files

PATTERNS = [
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{36,}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{60,}\b'),
    re.compile(rb'\bAKIA[A-Z0-9]{16}\b'),
    re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
]


def suspicious(path, data):
    """No matched values are returned or logged."""
    name = path.name.lower()
    secret_name = (name == '.env' or name.startswith('.env.')) and name != '.env.example'
    private_file = path.suffix.lower() in {'.key', '.pem', '.p12', '.pfx', '.keystore'}
    private_dir = bool(set(path.parts) & {'credentials', 'secrets', 'tokens'})
    return secret_name or private_file or private_dir or any(p.search(data) for p in PATTERNS)


def validate_configuration(path, data):
    """Deliberately limited schema checks; GitHub remains the final schema validator."""
    if path.parent.name == 'workflows':
        assert {'pull_request', 'push'} <= data['on'].keys()
        assert data['on']['push']['branches'] == ['main']
        assert data['permissions'] == {'contents': 'read'}
        for job in data['jobs'].values():
            assert job['timeout-minutes'] <= 15
            for step in job['steps']:
                if 'uses' in step:
                    assert re.fullmatch(r'[\w./-]+@[a-f0-9]{40}', step['uses'])
    elif path.parent.name == 'ISSUE_TEMPLATE' and path.name != 'config.yml':
        assert data['name'] and data['description'] and data['labels']
        inputs = [item for item in data['body'] if item['type'] != 'markdown']
        ids = [item['id'] for item in inputs]
        assert len(ids) == len(set(ids)) and 'ai' in ids
        assert all(item['attributes']['label'] for item in inputs)
    elif path.name == 'milestones.json':
        assert len(data) == 13
        assert len({item['title'] for item in data}) == 13
        dates = [datetime.fromisoformat(item['due_on'].replace('Z', '+00:00')) for item in data]
        assert dates == sorted(dates)
    elif path.name == 'labels.json':
        assert len({item['name'].casefold() for item in data}) == len(data)
        assert all(re.fullmatch(r'[a-fA-F0-9]{6}', item['color']) for item in data)
    elif path.name == 'dependabot.yml':
        assert data['version'] == 2
        assert all(item['package-ecosystem'] == 'github-actions' for item in data['updates'])


def main():
    failures = []
    count = 0
    for path in repository_files():
        if not path.is_file():
            continue
        count += 1
        relative = path.relative_to(ROOT)
        if path.is_symlink():
            failures.append(f'{relative}: symlink requires explicit repository policy review')
            continue
        content = path.read_bytes()
        if suspicious(relative, content):
            failures.append(f'{relative}: potential secret; inspect privately and rotate if exposed')
        try:
            if path.suffix in {'.py', '.sh', '.json', '.yml', '.yaml', '.md'}:
                text = content.decode('utf-8')
                assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines())
            if path.suffix == '.py':
                ast.parse(text, filename=str(relative))
            elif path.suffix == '.sh':
                subprocess.run(['bash', '-n', str(path)], check=True, capture_output=True)
            elif path.suffix in {'.json', '.yml', '.yaml'}:
                # JSON is a YAML subset. Keep config in this serialization for stdlib validation.
                validate_configuration(path, json.loads(text))
        except (ValueError, AssertionError, KeyError, TypeError, SyntaxError, subprocess.CalledProcessError):
            failures.append(f'{relative}: invalid syntax, configuration or whitespace (details withheld)')
    if failures:
        print('\n'.join(failures))
        return 1
    print(f'Repository checks passed ({count} files; configuration, Python/Bash syntax, whitespace and limited secret patterns).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
