#!/usr/bin/env python3
"""Publish maintained Wiki navigation pages; preserve unrelated Wiki pages.

Requires the first Wiki page to have been saved through GitHub's web interface.
Uses existing SSH credentials. No token is accepted or stored by this script.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = 'git@github.com:ham340i/Industrial-Data-Pipelinen-Platform.wiki.git'
SSH = 'ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes'


def git(*args, cwd=None):
    return subprocess.run(['git', '-c', f'core.sshCommand={SSH}', *args],
                          cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Commit and push changed maintained pages')
    args = parser.parse_args()
    pages = sorted((ROOT / 'docs/wiki').glob('*.md'))
    if not pages or not (ROOT / 'docs/wiki/Home.md').is_file():
        parser.error('Wiki sources, including Home.md, are required')
    stage = 'cloning the Wiki'
    try:
        with tempfile.TemporaryDirectory(prefix='local-pipeline-wiki-') as temp:
            checkout = Path(temp) / 'wiki'
            git('clone', REMOTE, str(checkout))
            stage = 'preparing maintained pages'
            for page in pages:
                shutil.copyfile(page, checkout / page.name)
            changes = git('status', '--short', cwd=checkout)
            if not changes:
                print('Wiki is already up to date.')
                return 0
            print(changes)
            if not args.apply:
                print('Preview only. Run with --apply to publish these maintained pages.')
                return 0
            # Reuse configured contributor identity without printing it.
            stage = 'reading the configured Git identity'
            for key in ('user.name', 'user.email'):
                git('config', key, git('config', key, cwd=ROOT), cwd=checkout)
            stage = 'committing maintained pages'
            git('add', '--', *(page.name for page in pages), cwd=checkout)
            git('commit', '-m', 'docs(wiki): publish capstone documentation navigation',
                '-m', 'AI-Assisted: Codex prepared navigation from repository documentation; human review remains pending.', cwd=checkout)
            stage = 'pushing the Wiki commit'
            git('push', 'origin', 'HEAD', cwd=checkout)
            print('Published Wiki commit ' + git('rev-parse', '--short', 'HEAD', cwd=checkout))
            return 0
    except subprocess.CalledProcessError:
        print(f'Failed while {stage}. Confirm the first page is saved, SSH access works, and Git identity is configured. No force push was attempted.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
