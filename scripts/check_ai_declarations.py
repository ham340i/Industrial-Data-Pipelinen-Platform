#!/usr/bin/env python3
# AI contribution: 50% or more AI-generated
"""Report source files that lack an AI-contribution declaration near the top.

The course rubric requires every team-written source file to declare one of
three levels. This script lists the files that do not, so each author can add
the level that is true for their file. It never guesses a level.

Usage: python3 scripts/check_ai_declarations.py [--strict]
"""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SUFFIXES = {'.py', '.ts', '.tsx', '.js', '.sh'}
# Generated or tool-owned files the rubric excludes.
EXCLUDED_PARTS = {'node_modules', 'dist'}
EXCLUDED_PREFIXES = ('migrations/versions/',)
DECLARATION = re.compile(
    r'AI contribution:\s*(no substantial AI-generated code|below 50% AI-generated|50% or more AI-generated)',
    re.IGNORECASE,
)
HEADER_LINES = 15


def applicable_files():
    listed = subprocess.run(['git', 'ls-files'], cwd=ROOT, check=True, text=True,
                            capture_output=True).stdout.splitlines()
    for name in listed:
        path = Path(name)
        if path.suffix not in SOURCE_SUFFIXES or EXCLUDED_PARTS & set(path.parts):
            continue
        if name.startswith(EXCLUDED_PREFIXES):
            continue
        yield name


def has_declaration(name):
    lines = (ROOT / name).read_text(encoding='utf-8').splitlines()[:HEADER_LINES]
    return any(DECLARATION.search(line) for line in lines)


def main():
    files = sorted(applicable_files())
    missing = [name for name in files if not has_declaration(name)]
    declared = len(files) - len(missing)
    for name in missing:
        print(name)
    share = 100 * declared // len(files) if files else 100
    print(f'{declared} of {len(files)} applicable source files declare their AI contribution ({share}%).')
    return 1 if missing and '--strict' in sys.argv[1:] else 0


if __name__ == '__main__':
    sys.exit(main())
