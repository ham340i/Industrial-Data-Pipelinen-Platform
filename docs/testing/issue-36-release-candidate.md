# Issue #36 verification: packaged Release 1 candidate

Issue: [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36). Branch: `feature/36-release-candidate`, based on main at `3d54b61`.

This record lists what was actually run and observed. It claims no release, tag or stakeholder acceptance; those gates are in the [tag checklist](../release-1/tag-checklist.md).

## What is verified, and where

| Acceptance criterion | Verified by | Where it runs |
|---|---|---|
| Repeatable Compose build, start, stop and validated configuration | `scripts/release_candidate.py` (`config`, `build`, `start`, `stop`, `status`); configuration unit tests | Script unit tests on every PR; real Compose in CI |
| Clean-install smoke harness with synthetic demo data and health checks | `release_candidate.py smoke`, scenario in `scripts/release_acceptance.py` | "Release candidate rehearsal" CI job |
| Persistence, backup, reset and restore; rollback and data-compatibility rules | `smoke` steps 3–4; manifest and data-safety unit tests; [candidate guide](../release-1/candidate.md#rollback-and-data-compatibility) | CI job and script unit tests |
| Test results, operator guide, limitations, demo recording instructions | This record, [candidate guide](../release-1/candidate.md), [release notes](../release-1/release-notes.md) | Documentation checks |
| Release notes and tag checklist, with no tag created | [Release notes](../release-1/release-notes.md), [tag checklist](../release-1/tag-checklist.md) | Review |

## Tests added

**Unit tests**, `scripts/tests/test_release_candidate.py`, standard library only. They use a fake Docker runner that records every Compose command:

- Configuration: the documented `.env.example` is valid. Unknown keys such as a password are refused, along with bad or equal ports, malformed or repeated lines, unknown log levels, project names that could leave the Compose namespace, and a missing settings file. CLI errors exit with status 1 and no traceback.
- Backup manifest: a matching backup is accepted. A tampered archive, an unknown format, or a schema newer than the candidate are refused, and the refusal names the release that wrote the backup.
- Data safety: `reset` and `restore` run nothing without `--yes`. Reset removes only this project's volumes. Backup stops before archiving and restarts only a stack that was running. A bad backup is refused before anything stops or is deleted. Restore streams exactly the verified archive into the stopped volume.
- Failure handling: `smoke` tears down and writes its report even when acceptance fails. It fails if containers survive teardown.

**Integration tests**, `tests/test_release_acceptance.py`. They run the same scenario module the Compose smoke uses, against the real API, engine and SQLite metadata:

- The Release 1 graph runs twice, every block's row counts match the oracle, and the Parquet rows are `A = 30`, `B = 50`. Everything reopens afterwards.
- Reopening a missing project, checking absence while the project still exists, a missing SQLite input, wrong output rows, and non-loopback targets all fail loudly instead of passing.

**Rehearsal**, `release_candidate.py smoke`. It runs on real Docker in the new CI job:

1. A clean install from an empty volume, with health checked on the API and through the frontend proxy.
2. The demonstration scenario over HTTP through the shipped frontend proxy.
3. The containers are recreated, and everything reopens.
4. Backup while running, reset, the candidate starts empty, restore, and everything reopens.

It always removes its containers and volume.

## Observed results

Local machine: macOS 26.6.2, Python 3.12.15. Docker is not installed on this machine, so the Compose rehearsal ran only in CI.

| Command | Result |
|---|---|
| `python -m pytest -q` | 1110 passed, 4 skipped (8 new) |
| `python3 -m unittest discover -s scripts/tests` | 40 passed (24 new) |
| `python -m ruff check`, `python -m ruff format --check`, `python -m mypy` | Clean; mypy strict on 115 files |
| `python -m mypy --strict` on both new scripts | Clean |
| `python3 scripts/check_repository.py`, `check_docs.py`, `check_release_plan.py` | Passed |
| `python3 scripts/release_acceptance.py --base-url http://127.0.0.1:8765 --workspace <temp>` against a real local API | Passed: two runs, rows `[["A", 30], ["B", 50]]` |
| In-container helper programs, run locally with the same arguments | Schema `0004` read; known schemas `0001`–`0004`; input written; a `../../` path refused |

CI result for the Compose rehearsal: recorded on the pull request once the "Release candidate rehearsal" job completes.

## Design decisions

- **One scenario, three uses.** The HTTP scenario module backs the backend integration test, the `demo` command and the CI rehearsal. The demonstration a tester sees is therefore the same one CI checks.
- **The scenario goes through the frontend's API proxy in Compose,** the path a browser uses, not straight to the API port.
- **Backups copy the volume while the containers are stopped,** so the SQLite file is consistent. The manifest records the checksum and schema revision so restore can refuse data before deleting anything.
- **Settings are an allowlist.** The candidate has three settings, so anything else in `.env` is treated as a mistake rather than passed through to Docker.
- **The rehearsal is its own CI job.** The repository caps jobs at 15 minutes, and the existing Compose job already spends most of that on its browser smoke.
- **Not done:** no `Release1` tag. A second-machine install, the demonstration recording, and stakeholder status remain on the tag checklist.
