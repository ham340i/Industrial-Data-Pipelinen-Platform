#!/usr/bin/env python3
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


def check_markdown(path, root=ROOT):
    text = path.read_text(encoding='utf-8')
    errors = []
    if not text.endswith('\n') or any(line.rstrip() != line for line in text.splitlines()):
        errors.append('missing final newline or trailing whitespace')
    for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', prose(text)):
        target = target.strip().strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            repo_prefix = '/ham340i/Industrial-Data-Pipelinen-Platform/'
            if parsed.netloc == 'github.com' and parsed.path.startswith(repo_prefix + 'blob/main/'):
                local = unquote(parsed.path.removeprefix(repo_prefix + 'blob/main/'))
            elif parsed.netloc == 'github.com' and parsed.path.startswith(repo_prefix + 'wiki/'):
                local = 'docs/wiki/' + unquote(parsed.path.removeprefix(repo_prefix + 'wiki/')) + '.md'
            else:
                continue
            # Validate maintained absolute links against this checkout, even
            # on a PR whose files are not yet on main or the live Wiki.
            target = '/' + local + ('#' + parsed.fragment if parsed.fragment else '')
            parsed = urlsplit(target)
        dest = (root / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/')
                else path.parent / unquote(parsed.path)) if parsed.path else path
        dest = dest.resolve()
        if not dest.is_relative_to(root.resolve()):
            errors.append('local link escapes repository')
        elif not dest.exists():
            errors.append(f'missing local target: {target}')
        elif parsed.fragment and dest.suffix.lower() == '.md':
            if unquote(parsed.fragment) not in heading_anchors(dest.read_text(encoding='utf-8')):
                errors.append(f'missing heading: {target}')
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
