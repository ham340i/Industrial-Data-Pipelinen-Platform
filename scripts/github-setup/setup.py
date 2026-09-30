#!/usr/bin/env python3
"""Create missing labels/milestones; preview by default, preserve existing records."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

CATALOG = Path(__file__).resolve().parent


def gh_json(args, payload=None):
    result = subprocess.run(
        ['gh', *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        # Do not echo server responses that might include sensitive content.
        raise RuntimeError('GitHub CLI request failed; verify authentication and permissions.')
    return json.loads(result.stdout)


def existing_records(repo, kind):
    records = []
    page = 1
    while True:
        query = f'per_page=100&page={page}'
        if kind == 'milestones':
            query += '&state=all'
        batch = gh_json(['api', f'repos/{repo}/{kind}?{query}'])
        records.extend(batch)
        if len(batch) < 100:
            return records
        page += 1


def reconcile(repo, kind, desired, existing, apply=False):
    key = 'name' if kind == 'labels' else 'title'
    indexed = {record[key].casefold(): record for record in existing}
    drift = False
    for record in desired:
        old = indexed.get(record[key].casefold())
        if old is not None:
            # GitHub normalizes milestone due times to midnight UTC. The
            # course catalog specifies calendar dates, not submission times.
            differs = any(
                (str(old.get(field, ''))[:10] != value[:10]
                 if kind == 'milestones' and field == 'due_on'
                 else old.get(field) != value)
                for field, value in record.items()
            )
            drift |= differs
            print(('DRIFT (unchanged): ' if differs else 'Exists: ') + record[key])
            continue
        print(('Create: ' if apply else 'Would create: ') + record[key])
        if apply:
            gh_json(['api', '--method', 'POST', f'repos/{repo}/{kind}', '--input', '-'], record)
        indexed[record[key].casefold()] = record
    return 2 if drift else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['labels', 'milestones'])
    parser.add_argument('--repo', default='ham340i/Industrial-Data-Pipelinen-Platform')
    parser.add_argument('--apply', action='store_true', help='Create missing entries; default is preview')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
        parser.error('--repo must be OWNER/REPO')
    try:
        desired = json.loads((CATALOG / f'{args.kind}.json').read_text())
        return reconcile(args.repo, args.kind, desired, existing_records(args.repo, args.kind), args.apply)
    except (OSError, RuntimeError, ValueError, KeyError):
        print('Setup failed. Check gh installation, authentication, repository access and catalog syntax.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
