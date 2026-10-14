# Issue #9 portable DAG verification

Status: implementation on `feature/9-portable-dag`, based on reviewed SDK
commit `8e816fa`, fast-forwarded onto merged main `80f8dc7` on October 14.
SDK PR #59 is merged; independent review and hosted CI for #9 remain pending.
No issue closure, release acceptance or stakeholder approval is claimed.

The fast-forward introduced no source-file changes relative to the tested SDK
revision. Local #9 and #13 files were preserved. The recorded October 13 checks
therefore still apply to the same implementation; tests were not rerun solely
for the unchanged SDK merge.

## Observed checks

On October 13, 2026, Codex ran the new graph suite in an isolated container
with Python 3.12 and repository-locked dependencies. The workspace was mounted
read-only for testing; temporary databases and test files stayed under `/tmp`.

Final observed results on the uncommitted issue #9 working tree:

| Check | Result |
|---|---|
| Full backend pytest suite | 267 passed; 12 existing deprecation warnings |
| New pipeline tests within that suite | 51 passed |
| Ruff lint | Passed |
| Ruff formatting | 35 files already formatted |
| Strict mypy | No issues in 35 source files |
| Documentation checks | 127 Markdown files passed |
| Repository-tool unittest suite | 16 passed |
| Release-plan validation | 34 items; ownership and dependency checks passed |
| Git whitespace check | Passed |

Tests used `python -m pytest -q -p no:cacheprovider --basetemp /tmp/dag-final`
inside the existing API image, with this workspace mounted at `/review`.
Static checks used `--no-cache` for Ruff and `/tmp` cache directories for mypy.
The first full pass exposed a missing import in a newly added test (263 passed,
one failed); the import was corrected and the final full suite passed. The
initial type-check failure in a heterogeneous test dictionary was also fixed.
No generated datasets or metadata databases were added to Git.

The Windows repository checker itself remains unverified for this branch: prior
session runs could not invoke Bash successfully. Its unit tests pass, and SDK
PR #59's hosted checks do not establish hosted checks for these new files.

The suite covers JSON round-trips, layout independence, stable ordering over
input permutations, empty/disconnected graphs, parallel dependencies, duplicate
IDs/connections, dangling references, cycles/self-loops, version policy,
portability and mutable config revalidation. SDK integration covers exact
version/config lookup, required inputs, named ports, cardinality and control/data
compatibility. A real disposable SQLite revision round-trip exercises storage.
Additional cases verify unsafe open/null/type/many output guarantees, optional
and many inputs, headless import without database initialization, and rejection
of mutated tuple/nonfinite/runtime config values before JSON serialization.

Reproduce with installed locked dependencies:

```powershell
python -m pytest tests/test_pipelines.py -q
python -m ruff check
python -m ruff format --check
python -m mypy
python -m pytest
python scripts/check_docs.py
```

## Limits and attribution

No blocks are executed by graph validation. UI and full ETL end-to-end tests do
not apply to this headless contract; integrated acceptance remains future work.
Performance/resource guarantees are not measured by this change. The SDK retains
its documented config/registry/preview limitations.

Karim requested issue #9 implementation. Codex designed and implemented the
models, tests and documentation and ran the recorded checks. No separate manual
implementation or verification by Karim is asserted. Planned reviewer:
`MarcElHaddad1`.
