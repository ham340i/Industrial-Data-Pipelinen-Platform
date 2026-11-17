#!/usr/bin/env python3
# AI contribution: 50% or more AI-generated
"""Check local and maintained repository/Wiki links, anchors and whitespace.

External URLs are not fetched; maintained GitHub links use local source files.
This is not a full Markdown parser:
reference-style links, embedded HTML and Mermaid semantics are outside its scope.
"""

from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def repository_files(root=ROOT):
    output = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root,
    )
    return sorted({root / name.decode() for name in output.split(b'\0') if name})


def prose(text):
    return re.sub(r'^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', text, flags=re.M | re.S)


def heading_anchors(text):
    counts = {}
    anchors = set()
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(text), re.M):
        slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(f'{slug}-{count}' if count else slug)
    return anchors


REPO_PREFIX = '/ham340i/Industrial-Data-Pipelinen-Platform/'


def maintained_target(target):
    """Map an absolute repository or Wiki URL to a local path; None if external."""
    parsed = urlsplit(target)
    if parsed.netloc != 'github.com':
        return None
    if parsed.path.startswith(REPO_PREFIX + 'blob/main/'):
        local = unquote(parsed.path.removeprefix(REPO_PREFIX + 'blob/main/'))
    elif parsed.path.startswith(REPO_PREFIX + 'wiki/'):
        local = 'docs/wiki/' + unquote(parsed.path.removeprefix(REPO_PREFIX + 'wiki/')) + '.md'
    else:
        return None
    return '/' + local + ('#' + parsed.fragment if parsed.fragment else '')


def link_error(path, root, target):
    """Return the problem with one local link, or None when it resolves."""
    parsed = urlsplit(target)
    dest = (root / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/')
            else path.parent / unquote(parsed.path)) if parsed.path else path
    dest = dest.resolve()
    if not dest.is_relative_to(root.resolve()):
        return 'local link escapes repository'
    if not dest.exists():
        return f'missing local target: {target}'
    if parsed.fragment and dest.suffix.lower() == '.md':
        if unquote(parsed.fragment) not in heading_anchors(dest.read_text(encoding='utf-8')):
            return f'missing heading: {target}'
    return None


def check_markdown(path, root=ROOT):
    text = path.read_text(encoding='utf-8')
    errors = []
    if not text.endswith('\n') or any(line.rstrip() != line for line in text.splitlines()):
        errors.append('missing final newline or trailing whitespace')
    for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', prose(text)):
        target = target.strip().strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            # Validate maintained absolute links against this checkout, even
            # on a PR whose files are not yet on main or the live Wiki.
            target = maintained_target(target)
            if target is None:
                continue
        error = link_error(path, root, target)
        if error:
            errors.append(error)
    return errors


def main():
    failures = []
    paths = [p for p in repository_files() if p.suffix.lower() == '.md' and p.is_file()]
    for path in paths:
        for error in check_markdown(path):
            failures.append(f'{path.relative_to(ROOT)}: {error}')
    if failures:
        print('\n'.join(failures))
        return 1
    print(f'Documentation checks passed ({len(paths)} Markdown files; local inline links/anchors and whitespace).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
