# Issue #26 local verification

Scope: the [implemented selected-node preview contract](../architecture/selected-node-preview.md), including bounded CSV/JSON/Parquet-to-Select previews, project-local resources, safe errors, ephemeral UI state and hidden-example compatibility. The approved extension excludes SQL/SQLite preview and catalog integration; existing standalone SQL behavior is unchanged.

## Environment

Windows, Node 24.22.2, Python 3.13.1 in `.venv`, Playwright 1.63.0 with installed Microsoft Edge. The repository targets Python 3.12; these local checks do not establish Python 3.12 CI or independent acceptance. Commands use fresh ignored pytest directories and synthetic file inputs. Browser tests use isolated SQLite/workspace/output paths under `frontend/test-results`.

## Results

- Backend preview coverage: 73 cases across `test_preview.py` and `test_file_preview.py` (the original JSON/Parquet rejection cases were replaced by supported-source coverage). Covers source/schema/count/null behavior, bounded prefix reads, JSON encodings/duplicate keys/nested values, Parquet metadata/row-group budgets, actual read caps, cancellation during reading, project isolation/bindings, request/response/ancestor limits, concurrency and no-store errors.
- Full backend regression: 781 passed, including all 73 preview cases. Existing Starlette/SQLite deprecation warnings remain (54 warnings).
- Frontend unit tests: 124 passed across 16 files. Includes sample/metadata provenance and consistent known counts on truncated Parquet samples, alongside manual-only requests, empty/unsupported states, structured errors, refresh failures, cancellation/late replies and semantic/node/output/limit/project/generation invalidation.
- Browser: eight real API scenarios passed, including direct JSON/Parquet sources and their Select projections, CSV preview, saved-example compatibility, configuration, file-block authoring, graph save/reopen and validation. All three preview scenarios passed again after correcting the panel's source-support label. Desktop and 390 px screenshots were inspected; no horizontal document overflow was found. React Flow emitted transient resize warnings without failing a scenario.
- Mypy passed all 84 configured Python files. Ruff lint/format checks, frontend ESLint, TypeScript and production build passed. Formatting checks are scoped to changed frontend files; repository-wide pre-existing formatting warnings are not claimed fixed.
- Documentation links/whitespace, repository checks, release-plan checks and `git diff --check` passed. Ownership, estimates and dependencies remain unchanged.

The preview browser scenarios read actual CSV, JSON and generated Parquet files, check schema/null tabs and sample/full count provenance, exercise Select Columns and malformed inputs, check 390 px overflow, and confirm no output file, run record or new saved revision. CSV also exercises unsaved projection changes and empty/missing input. Screenshots are ignored browser artifacts. A temporary config runs API/Vite on ports 8001/3001 with isolated metadata/workspaces; the user's servers and data are unchanged.

## Bounded-prefix measurements

The JSON/Parquet extension was measured locally on 2026-11-11 through `Block.preview`, using synthetic inputs with 100,000 rows and a 20-row request. Parquet was written with 1,024-row groups. Five warm calls were measured with Python allocation tracing enabled:

| Source | File bytes | Read bytes | Returned / inspected rows | Full count | Median time | Traced Python peak |
|---|---:|---:|---|---|---:|---:|
| JSON | 3,060,002 | 1,024 | 20 / 21 | Unknown | 1.49 ms | 49,272 bytes |
| Parquet | 993,490 | 75,470 | 20 / 20 | 100,000, from metadata | 1.36 ms | 89,879 bytes |

These reader measurements exclude API/network/browser overhead and fixture preparation. Python tracing does not capture all native Arrow allocations and is not RSS evidence. The Parquet policy bounds declared decoding work and checks materialized batches; it is not a hard memory boundary against corrupt metadata or native codecs.

The following CSV measurement predates the extension and is retained as historical evidence, not a direct latency comparison:

A local TestClient measurement used a synthetic CSV with 100,000 rows / 1,168,900 bytes and a CSV-to-Select path. With limits of 20 rows / 2,000 cells, the response returned 20 rows after inspecting 21 rows and reading 122 bytes. The JSON response was 818 bytes; full count correctly remained null. Five requests after warmup, with Python allocation tracing enabled, had a median API time of 11.71 ms (11.21–13.13 ms range), with a traced Python-allocation peak of 174,510 bytes across those requests.

This is a small local prefix measurement, not a throughput guarantee or a native/RSS memory measurement. It excludes HTTP network/browser time and does not establish hard OS I/O deadlines. Input preparation and imports occurred before tracing; the complete backend/browser suites provide separate correctness evidence.

## Reproduction

```powershell
# Repository root, using the development interpreter and a fresh basetemp:
$pytestRunPath = Join-Path $PWD.Path ('.venv\pytest-preview-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp $pytestRunPath
.\.venv\Scripts\python.exe -m mypy

# From frontend, with Node 24 on PATH:
npm test
npm run lint
npm run build
# Stop conflicting test-port servers first, and set LPS_PYTHON as needed:
npm run test:standalone -- preview.spec.ts
```

The standalone config defaults to an isolated test metadata database and workspace under `test-results`; explicitly provided environment settings override those defaults. Playwright screenshots/traces use a separate `test-results/standalone` directory. `LPS_STANDALONE_API_URL` can point API fixture setup at an isolated test API, paired with the frontend's `VITE_API_BASE_URL` and the backend's allowed origin. Normal app configuration is unchanged.

## Assistance and limits

OpenAI Codex implemented and tested the approved file-source scope and drafted the documentation. Independent human review, GitHub Actions and live issue acceptance have not been performed. Generic Run-to-Here, SQL preview, process memory isolation and hard I/O timeouts are not claimed. The source readers do not change normal file execution, create database migrations or introduce dependencies.
