# Repository validation

Local validation performed during this repository-foundation change, completed 2026-09-29. Environment: macOS, Python 3.13.0, Bash; application baseline `71a1383` plus the uncommitted repository changes. No new commit or GitHub Actions run is claimed.

| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts/tests -v` | PASS — 9 repository-tool tests |
| `python3 scripts/check_repository.py` | PASS — configuration, Python/Bash syntax, whitespace and limited secret-pattern checks |
| `python3 scripts/check_docs.py` | PASS — 43 Markdown files; local inline links, heading anchors and whitespace |
| `git diff --check` | PASS — tracked patch whitespace; repository checker also covers new files |
| GitHub setup wrapper `--help` commands | PASS — both wrappers invoke the setup utility |
| `git check-ignore` on representative sensitive paths | PASS — environment files, credentials, tokens, local data and generated outputs ignored |
| Application install / lint / type checks / tests / build | Not applicable: no application, manifest, lockfile or framework exists |
| GitHub Actions remote execution | Not run / unverified |
| GitHub setup against live API | Not run: gh unavailable; reconciliation tested with mocked API |

## Scope and limitations

The tests check broken local links/headings, escaping paths, whitespace, ignored fenced examples, suspicious secret patterns, unsafe workflow permissions, setup preview behavior, preservation of existing settings, idempotency and milestone pagination. Synthetic token-shaped strings are constructed only inside tests; no credentials are used.

The Markdown checker covers local inline links and ordinary heading anchors; it does not fetch external URLs or parse reference-style links, embedded HTML or Mermaid semantics. Configuration files use JSON syntax, a valid YAML subset, so the Python standard library can parse them without a dependency installation. Structural checks cover selected rules, not GitHub’s entire remote schema. Keep this serialization when editing `.yml` files, or deliberately add a maintained YAML parser and locked tooling dependencies if the team chooses standard block YAML later.

## Wiki follow-up validation

Prepared eight topic/home pages plus sidebar and footer, and a preview/apply publisher. Repository checks passed for 72 files, documentation checks passed for 54 Markdown files, and the nine existing tool tests passed. All 67 Wiki links to maintained pages or repository documents were checked against local source paths and heading anchors. The publisher help command passed. Live publication remains blocked: the Wiki setting is enabled, but both SSH and HTTPS returned repository-not-found when publication was attempted.

Actions are pinned to a commit SHA with read-only contents permissions, no secrets and no persisted checkout credentials. Dependabot is configured for Actions only. No dependencies exist to install/cache/audit; application gates must be added with the first implementation. Secret scanning here is deliberately limited and does not guarantee absence of secrets.
