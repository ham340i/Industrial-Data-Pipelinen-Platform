# Issue #7 SQLite metadata verification

Scope: [issue #7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), Iteration 1. Branch: `feature/7-sqlite-metadata`, based on main after workspace PR #47. Design: [ADR-0002](../architecture/decisions/ADR-0002-sqlite-metadata.md). Operations: [metadata guide](../metadata.md).

Implementation revision: [4fdeb17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/commit/4fdeb17e113f699cb6afe02e05765fdc1d23f717). [PR #48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48) contains the exact head and final check results; [current CI checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48/checks). `joedaswagger` was requested as reviewer. Subsequent evidence-link edits do not alter the implementation tested locally.

## Actual local observations

Environment: Windows, CPython 3.12.10, isolated `.venv`, dependencies installed from the regenerated hash-pinned `requirements.lock`, SQLite files in pytest temporary directories. No manufacturing datasets or real secret values are used.

The backend pytest suite passed **72 tests** on October 4, 2026. The new [metadata tests](../../tests/test_metadata.py) cover:

- All seven entities and relationships round-trip through a reopened file database.
- Portable exports exclude private path/provider references stored in separate bindings; nested reserved fields, absolute paths, invalid JSON values and typed Core insert bypass attempts are rejected.
- Every new/reconnected SQLite connection enforces foreign keys; failed transactions remove earlier flushed writes and transactional DDL.
- Invalid names, duplicate identities, bad foreign keys, non-positive revisions, invalid run states/times and negative row counts fail at persistence boundaries.
- Revision editing through the ORM is rejected; exported copies cannot mutate stored history; new revisions leave existing runs attached to the original.
- Initial upgrade, repeated upgrade, drift comparison, downgrade and re-upgrade succeed; unrelated data survives downgrade.
- A forced failure after several migration tables are created rolls back schema/version changes and permits a subsequent successful upgrade.
- Actual FastAPI lifespan startup creates/reuses the schema, closes database resources and fails for an unknown migration version. Existing HTTP contracts continue to pass.
- Module import creates no metadata files; the destructive CLI downgrade requires explicit confirmation.

Commands: `python -m ruff check`, `python -m ruff format --check`, `python -m mypy`, `python -m pytest -q`. The final local check results and remote checks are recorded in the linked PR. Nine existing FastAPI/Starlette deprecation warnings appeared; they do not fail the suite. No performance benchmark or full ETL workflow is claimed.

An additional synthetic demonstration launched actual Uvicorn on an ephemeral loopback port with a temporary `LPS_METADATA_PATH`. HTTP health succeeded after all seven metadata tables were migrated. A SQLAlchemy project write committed, the API process restarted against that same file, and the project was successfully reloaded. Both processes were stopped and temporary data removed. This is a Codex-run demonstration, not the student's required personal presentation.

The existing subprocess harness used POSIX `/dev/null` as pytest configuration. It now writes an isolated temporary `pytest.ini` so the real failure controls work on Windows and Linux.

## Container and CI evidence

The existing `Compose workspace smoke` job now inserts a synthetic `Project` through SQLAlchemy into the startup-migrated database, recreates containers and reloads that same project. This replaces the plain-text marker as persistence evidence. It continues checking real HTTP health, browser connectivity, assets, SPA fallback, proxy routing, non-root execution and isolated teardown.

Docker is unavailable on this local Windows environment, so container verification must be confirmed from the PR's actual CI run. No local Compose success is asserted. Repository/documentation checks and frontend/Compose checks retain their existing CI gates.

## Acceptance and attribution

Implementation and local test evidence are ready for independent review by `joedaswagger`. Approval, merge, issue closure, iteration demonstration and stakeholder acceptance are not asserted here. Codex generated this implementation and verification; Al-Yousef requested the work. Human understanding, review and any personally authored changes must be recorded when they actually occur.
