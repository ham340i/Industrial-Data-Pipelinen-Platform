# Issue #54 SQL result correctness

Scope: [issue #54](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/54), correcting the three findings in [PR #52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52). Base: `5f1f5d67d35f0f013c46934c8d1685406bf79d30`. Branch: `fix/sql-spike-results`; target: `feature/12-safe-sql-connectivity`. The original spike commits remain attributed to adamoug; no approval or merge is asserted here.

## Design and alternatives

URI construction uses a percent-encoded absolute file URI before appending the read-only query option. SQLite treats raw fragments and percent escapes as URI syntax, so the previous literal string concatenation did not necessarily open the configured filename. See [SQLite's URI rules](https://www.sqlite.org/uri.html).

For SQL, a quote-aware masked inspection view supports the existing bounded validation while the original query goes to SQLite. Quoted strings/identifiers and actual comments are masked only for keyword/separator inspection. This avoids rewriting data, including doubled quotes and semicolons inside literals. A new parser package is unnecessary for this SQLite-only spike; SQLite remains the parser and the existing authorizer remains the execution guard. This is not a production SQL security model. See [SQLite authorizer behavior](https://www.sqlite.org/c3ref/set_authorizer.html) and [Python's single-statement execute contract](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Cursor.execute).

Identical result aliases are rejected before fetching rows. Requiring explicit unique aliases keeps the existing dictionary-based result contract. Positional pairing preserves distinct values for aliases differing by case; `sqlite3.Row` name lookup would otherwise select the same value for both.

## Regression baseline

After correcting a misplaced return in the new test fixture, the original production code produced **15 failures and 26 passes** across the existing SQL tests plus 18 added cases. Failures cover special filename selection and real connection write protection; unchanged quoted literals/names and actual comments; duplicate aliases; and distinct case-sensitive result values. The test-authoring fixture mistake is separate from production defects and is not counted as the regression baseline.

After the implementation, those same 41 SQL cases passed. Four additional tests verify that actual writes/statement separators remain rejected and a write attempted inside a SELECT callback is denied by SQLite's authorizer.

## Local verification

Environment: Windows, Python 3.12.10. The neighboring metadata PR virtual environment supplies the same locked API/testing dependencies; extra metadata packages are unused by this spike. Synthetic temporary SQLite databases only.

- `python -m pytest -q`: 69 passed, including all 45 SQL cases (23 original and 22 added). Nine existing Starlette deprecation warnings remain.
- `python -m ruff check .` and `python -m ruff format --check .`: passed; 16 Python files formatted.
- `python -m mypy`: passed across 16 source files.
- `python scripts/check_repository.py`, `python scripts/check_docs.py` and `python scripts/check_release_plan.py`: passed. The release plan retains the original 34 items, eight students, estimates and acyclic dependencies.
- `python -m unittest discover -s scripts/tests -v`: 16 passed.
- `git diff --check`: passed.

These local results precede the final evidence-only documentation update. Exact commit and hosted CI results are recorded in the follow-up PR.

The two pytest harness subprocesses use the identical temporary-INI portability correction already proposed in [PR #51](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/51) and [PR #48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48), enabling the full suite on Windows without POSIX `/dev/null`. No weaker failure assertions are introduced.

Docker is unavailable on this host. Hosted clean installs and real Compose CI must pass before integration. No frontend/API route, dependency, production connector, stakeholder approval or benchmark is added.

## AI assistance

Codex reproduced the defects, implemented these corrections, wrote/ran tests and prepared this evidence at Al-Yousef's direction. Independent teammate review is tracked in PR #55. Adam's original spike implementation and disclosure are preserved.
