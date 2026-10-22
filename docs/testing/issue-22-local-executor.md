# Issue #22 verification

Scope: deterministic local DAG execution, per-run Polars data/schema storage,
SDK lifecycle reuse, failure propagation, cancellation and retention budgets.
Implementation branch: `feature/22-local-dag-executor`, based on `2a37c3c`
(the existing issue #10 proof branch). These changes reuse that prerequisite;
merging the prerequisite remains a delivery dependency.

Synthetic coverage includes reordered diamond DAGs, stable fan-in ordering,
independent branches after failure, transitive skipping, hooks, validation before
execution, input mutation isolation, detached configuration, empty/null schema,
control signals, cancellation, observer exceptions, numeric overflow/precision,
runtime schema failures, structured redaction and graph/data limits. The golden
integration runs the existing CSV → select → Parquet fixture through the new
executor and verifies the resulting file.

Verification was performed by Codex on October 21, 2026. Final commands and
results are recorded below. No human manual demonstration or hosted CI result
is implied. UI E2E is deferred to Iteration 4 because #22 has no UI/API wiring.

Designated reviewer Al-Yousef has not yet reviewed this implementation.
Production catalog integration (#16/#18/#20), independent review, PR/CI and
stakeholder acceptance are not claimed complete by these synthetic tests.

AI assistance: Codex authored implementation, tests and documentation and ran
local checks at the user's request. Human code review remains pending.

## Observed results

- macOS Python 3.13 virtual environment, hash-pinned root dependencies:
  `python -m pytest -q`: **389 passed**, including 15 executor cases.
- Linux ARM64 Python 3.12 application image, current working tree mounted
  read-only: `python -m pytest -p no:cacheprovider -q`: **389 passed**.
  Both environments report 38 existing Starlette deprecation warnings.
- `python -m ruff check`: passed.
- `python -m ruff format --check`: 48 files formatted.
- `python -m mypy`: no issues in 48 source files.
- `python3 scripts/check_repository.py`, `python3 scripts/check_docs.py`,
  `python3 scripts/check_release_plan.py` and `git diff --check`: passed.
- `docker compose up --build --detach --wait`: frontend and API healthy with
  the regenerated hash-pinned Polars/Arrow dependencies.

Results describe uncommitted changes on the branch above, not a published
revision. GitHub CLI is unauthenticated in this environment; no PR, review
request, issue closure or hosted CI result was created.
