# SQL source and workflow verification (#23, #31)

Date: November 3, 2026. Base revision: `5f0f811`; branch:
`feature/23-sql-source-workflow`. Results below apply to the local working tree,
not a merged commit or GitHub Actions run. Fixtures are synthetic. No stakeholder
credentials, datasets or acceptance were used.

## Design and scope

See [SQL source design](../design/issue-23-sql-source.md),
[operator guide](../sql-source.md), and
[release graph](../examples/sql-join-pipeline.json).

Issue #23's prerequisites #12 and #16 were closed when inspected. The registered
SQL block implements the approved local SQLite scope with runtime resource
resolution, named binding, read-only connection policy, bounded reads, explicit
SDK schema/Polars conversion and structured failures. Remote credential providers
are outside the approved SQLite demonstration scope.

Issue #31 is partial and must remain open. Prerequisites #26, #28, #30 and #33
were open when inspected. Current execution writes a real Parquet file, but
run telemetry has no artifact indexing yet. The nested object schemas used by
quality/aggregate blocks also exceed the current form renderer's supported
subset. Preview, full UI authoring and artifact-row inspection are unverified.
Do not interpret the SQL-only browser test as full release UI acceptance.

## Executed checks

Environment: macOS, Python 3.12.16, Node 24.19.0, repository-locked Python/npm
packages. Playwright downloaded Chromium 153 into a temporary browser directory.

| Command | Observed outcome |
|---|---|
| `.venv/bin/python -m pytest -q` | 722 passed; existing deprecation warnings |
| `.venv/bin/python -m pytest tests/test_sql_block.py tests/test_sql_source_execution.py -q` | 46 passed, including result byte budget and policy-bypass checks |
| `.venv/bin/python -m ruff check` | Passed |
| `.venv/bin/python -m ruff format --check` | Passed |
| `.venv/bin/python -m mypy` | Passed, 77 source files |
| `.venv/bin/python scripts/check_repository.py` | Passed |
| `python3 scripts/check_docs.py` / `git diff --check` | Passed |
| `npm run check --prefix frontend` | Passed: lint, formatting, types, 110 tests, production build |
| `LPS_PYTHON="$PWD/.venv/bin/python" PLAYWRIGHT_BROWSERS_PATH=/tmp/industrial-playwright npm run test:release --prefix frontend` | 1 passed, real API/Vite/Chromium, 17.8 seconds |

The browser scenario creates a project and database fixture, authors a SQL source
in the UI, saves/runs it, verifies two rows, reloads/reopens/reruns it, and changes
the query to verify a structured failure. No engine or HTTP stubs are used.
The dedicated config creates isolated metadata/workspaces in the OS temporary
directory and refuses existing servers on ports 8000/3000.

The API integration test saves and reloads the complete release graph, executes
it twice through the real executor, checks block state/timing/count/log evidence,
and reads the Parquet output to verify the exact aggregate. Negative SQL tests
cover parameters/injection, nulls and empty schemas, unsupported data, workspace
escape, query failure, row/VM budgets and path/query redaction. Existing spike
tests also prove write rejection and read-only file permissions.

An early integration assertion expected indexed run outputs and failed because
#28 is not implemented. The final assertion verifies measured sink input count
and reads the actual Parquet file; missing artifact indexing stays documented.

## Attribution and outstanding review

OpenAI Codex generated the design, implementation, tests and these records and
executed the listed checks. The user supplied task scope and GitHub identity.
The existing `app/sources/sql.py` row-width-check edit was retained, adding an
explicit `strict=False` to its zip call for the repository lint rule. No claim
of manual student authorship, reviewer approval or stakeholder signoff is made.

No issue has been closed and no PR, CI run or merge is asserted. Planned
reviewers remain @joedaswagger for #23 and @karimikhaeil for #31. Human review,
CI and remaining dependency integration are required before completion.
