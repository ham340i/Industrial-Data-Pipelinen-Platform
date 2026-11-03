# Testing Evidence

Status: Issue #25 evidence recorded on November 2, 2026. This is Al-Yousef's
allocated backend scope; whole-iteration UI acceptance is not asserted.

## Automated Tests

On `main` at `e03177334f7a89b1d6ca4560e849884a8a22e532`: 677 backend tests
passed, with one existing Windows symlink restriction skip. The run includes
71 quality unit/catalog cases and 13 quality executor/publication cases.
Ruff lint/format and mypy passed. See the
[requirement mapping and commands](../../testing/issue-25-data-quality.md#november-2-2026-current-main-recheck).

## Integration Tests

Real CSV source -> quality block -> executor -> CSV sink cases verify invalid
required checks create no output and preserve prior files; optional warnings,
valid checks and explicit fill/drop publish literal expected contents. Empty
tables and declared-nullability mismatches are included. All 13 cases passed
within the full run; this is filesystem/executor integration, not browser E2E.

## Manual Verification

Codex ran the [synthetic headless demonstration](demo.md). Required null failure
skipped publication; explicitly optional mode warned and published. No student
manual execution or live team/stakeholder demonstration is inferred.

## CI Results

PR #71 head `79bfb312a21fc286bd9d30fef0956941091ca068` has successful
[CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/41213983037)
and [documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/41213983049)
runs, re-read November 2. Those are pre-merge hosted runs, separate from the
November 2 local current-main checks. No fresh current-main hosted run is claimed.

## Failed Tests / Known Problems

The existing symlink case cannot execute on this Windows host. Forty-seven
existing dependency deprecation warnings were reported. A demonstration under
restricted file access failed its optional-publication assertion; the unchanged
script passed with normal local file access. UI/E2E acceptance remains for
Iteration 4. No unresolved #25 backend failure was found in this audit.

## Environment

Windows, Python 3.12.10, fresh virtual environment using hash-pinned
`requirements.lock`, Polars 1.44.2 and PyArrow 25.0.1. Synthetic data only.

## Commands Used

From the repository root using the isolated environment's Python:

```sh
python -m pytest -q --basetemp=../verification/pytest-main --junitxml=../verification/backend-main.xml
python -m ruff check
python -m ruff format --check
python -m mypy
python scripts/demo_data_quality.py
```

The temporary verification directory is local audit output, not a repository
dependency. The full suite took 24.42 seconds; XML identifies all 84 quality
cases as passing.

## Evidence Links

- [Issue #25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25)
- [Approved and merged PR #71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71)
- [Current verification](../../testing/issue-25-data-quality.md)
- [Al-Yousef's contribution and review evidence](../../individual-contributions/Al-Yousef-iteration-3.md)

AI assistance: Codex performed this audit, ran the checks and drafted this
record at Yousef's request. Human learning, actual hours, academic submission
and stakeholder signoff are not inferred.
