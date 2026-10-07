# Issue #8 Block SDK verification

Scope: [issue #8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8).
Design/usage: [SDK guide](../block-sdk-draft.md) and
[architecture](../architecture/block-sdk-release-1.md).

Verification date: October 6, 2026. Tested working tree based on commit
`764944b4d27a997a5b1a903883544107c3aba1f9`; the SDK changes were uncommitted at
verification time. This base commit alone does not contain the tested SDK.

Environment: Windows, CPython 3.13.1, local `.venv` created with system package
access, repository hash-pinned dependencies installed from `requirements.lock`,
pytest 8.4.2. Python 3.12 is the repository/CI target but was not available in this
local environment. No dependency files or CI configuration were changed.

## Actual results

| Check | Observed result |
|---|---|
| SDK tests | 89 passed |
| Full backend suite | 215 passed |
| Ruff lint | Passed |
| Ruff formatting | 32 files already formatted |
| mypy | No issues in 32 source files |
| Standalone synthetic demonstration | Expected output, one preview row, events and typed metadata; no API/ORM imports |

Commands executed from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check
.\.venv\Scripts\python.exe -m ruff format --check
.\.venv\Scripts\python.exe -m mypy
$pytestRunPath = Join-Path $PWD.Path ('.venv\pytest-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp $pytestRunPath
```

The full suite emitted 12 existing FastAPI/Starlette deprecation warnings. The
SDK itself is headless; the shared test conftest imports the existing API client.
Using a fresh temporary test directory avoids clearing earlier folders with
different Windows permissions, and disabling the cache avoids `.pytest_cache`.

## Acceptance coverage

| Acceptance area | Implemented behavior and evidence |
|---|---|
| Identity | ID/version/type/name/category models; blank/duplicate declarations rejected; distinct versions coexist |
| Ports/config/data | Strict BlockConfig/defaults; distinct control/table types; required/many rules; columns/types/nullability and compatibility checks |
| Validation/execution/preview/context/log hooks | Pure validation; deterministic sample; before/after hooks; node/run events; bounded optional preview; sink preview unsupported |
| Failures/public metadata | BlockFailure/BlockMetadata JSON round-trips; credential/handle rejection; redacted exceptions; broken logger preserves success/original error |
| Registry/example/fixtures/docs | Atomic registration, exact versions, unchanged export snapshots, synthetic golden/negative fixtures and complete extension guide |

Tests in [test_blocks.py](../../tests/test_blocks.py) also check malformed
inputs/outputs, invalid defaults and schema aliases, registration failures leaving
the catalog unchanged, changed registered identities/config models, lifecycle
mutations, and shared preview budgets across outputs. The golden fixture and
negative fixture are reviewed synthetic JSON, not partner datasets.

## Standalone demonstration

An actual `.venv\Scripts\python.exe -c` invocation loaded
`tests/fixtures/blocks/add_constant.json`, registered `AddConstantBlock`, resolved
`synthetic.add_constant@1.0.0`, and used these SDK calls:

```python
output = block.run(fixture["config"], inputs, context)["table"][0]
sample = block.preview({}, inputs, context, PreviewLimits(max_rows=1))["table"][0]
BlockMetadata.from_public(registry.public_metadata()[0])
```

Observed output: input values `[2, -1, 0]` with amount `3` produced `[5, 2, 3]`;
the default-config preview returned one row. Logged events were `started`,
`succeeded`, `previewed`. Assertions confirmed `fastapi`, `sqlalchemy` and
`app.main` were absent from `sys.modules`. No resource callback, API service or
database was needed. The guide supplies a complete reproducible headless example.

## Review and attribution

The user approved the draft, reviewed the narrowed plan and explicitly authorized
implementation. Independent review by the issue's designated reviewer,
issue-linked PR/remote CI, and later integrated UI acceptance evidence remain
pending; none are represented as completed local checks. Local execution does not
establish a Python 3.12 test result or stakeholder acceptance.

Codex generated the implementation, fixtures/tests, documentation and verification
record within the approved issue scope. See the [AI disclosure](../ai-usage.md).
No processing libraries, production block catalog, engine, API/frontend changes,
providers or database/migration changes were introduced.
