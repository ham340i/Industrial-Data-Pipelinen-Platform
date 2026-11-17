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
- Rollback: restore builds the checked-out revision before checking schemas or stopping, and restarts with recreated containers. A schema unknown to the rebuilt image is refused before stopping. The rollback rehearsal fails if newer-schema data is ever accepted. Every accepted setting is consumed by `compose.yml`.
- Failure handling: `smoke` tears down and writes its report even when acceptance fails. It fails if containers survive teardown.

**Integration tests**, `tests/test_release_acceptance.py`. They run the same scenario module the Compose smoke uses, against the real API, engine and SQLite metadata:

- The Release 1 graph runs twice, every block's row counts match the oracle, and the Parquet rows are `A = 30`, `B = 50`. Everything reopens afterwards.
- Reopening a missing project, checking absence while the project still exists, a missing SQLite input, wrong output rows, and non-loopback targets all fail loudly instead of passing.

**Rehearsal**, `release_candidate.py smoke`. It runs on real Docker in the new CI job:

1. A clean install from an empty volume, with health checked on the API and through the frontend proxy.
2. The demonstration scenario over HTTP through the shipped frontend proxy.
3. The containers are recreated, and everything reopens.
4. Backup while running, reset, the candidate starts empty, restore, and everything reopens.
5. Rollback: a backup from a schema the candidate does not know is refused without changing data, then the older backup is restored and everything reopens.

It always removes its containers and volume.

## Observed results

Local machine: macOS 26.6.2, Python 3.12.15. Docker is not installed on this machine, so the Compose rehearsal ran only in CI.

| Command | Result |
|---|---|
| `python -m pytest -q` (after merging main with #105) | 1114 passed, 4 skipped (8 new) |
| `python3 -m unittest discover -s scripts/tests` | 45 passed (29 new) |
| `python -m ruff check`, `python -m ruff format --check`, `python -m mypy` | Clean; mypy strict on 118 files |
| `python -m mypy --strict` on both new scripts | Clean |
| `python3 scripts/check_repository.py`, `check_docs.py`, `check_release_plan.py` | Passed |
| `python3 scripts/release_acceptance.py --base-url http://127.0.0.1:8765 --workspace <temp>` against a real local API | Passed: two runs, rows `[["A", 30], ["B", 50]]` |
| In-container helper programs, run locally with the same arguments | Schema `0004` read; known schemas `0001`–`0004`; input written; a `../../` path refused; schema stamped to `9999_newer_release` and read back |

CI: the "Release candidate rehearsal" job passed on real Docker at `d5fb614` ([run 44162489929](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44162489929)) and `952e7f8` ([run 44164711720](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44164711720)), before the rollback step was added. The run for the review fixes is recorded on the pull request.

## ham340i's review of PR #106 at 952e7f8

1. **Restore could reuse a newer image during rollback (P1).** After checking out an older revision, restore read the known schemas from whichever API image was cached, and restarted without rebuilding. A newer candidate that was still running could reopen the restored data and migrate it forward again. **Fixed:** restore now builds the checked-out revision's images first, checks the backup against that build, and restarts on freshly created containers (`--force-recreate`). Unit tests pin the order: build, then schema check, then stop, then recreate. The rehearsal gained step 5: the live database is stamped with a schema this candidate does not know, as a newer release's data would be. Restore must refuse that backup without changing the data, then roll back to the older backup and reopen everything, on real containers. **Limit:** CI still builds one revision. A rollback between two real Git revisions with different migrations is simulated by the stamped schema, not checked out.
2. **`LPS_LOG_LEVEL` was accepted but had no effect (P2).** True at the time: `compose.yml` did not forward it. **Fixed by merging main:** #105 forwards it to the API and configures logging from it. A new test checks that every setting the candidate accepts is consumed by `compose.yml`, so a validated setting cannot silently do nothing again.

## Design decisions

- **One scenario, three uses.** The HTTP scenario module backs the backend integration test, the `demo` command and the CI rehearsal. The demonstration a tester sees is therefore the same one CI checks.
- **The scenario goes through the frontend's API proxy in Compose,** the path a browser uses, not straight to the API port.
- **Backups copy the volume while the containers are stopped,** so the SQLite file is consistent. The manifest records the checksum and schema revision so restore can refuse data before deleting anything.
- **Settings are an allowlist.** The candidate has three settings, so anything else in `.env` is treated as a mistake rather than passed through to Docker.
- **The rehearsal is its own CI job.** The repository caps jobs at 15 minutes, and the existing Compose job already spends most of that on its browser smoke.
- **Not done:** no `Release1` tag. A second-machine install, the demonstration recording, and stakeholder status remain on the tag checklist.
