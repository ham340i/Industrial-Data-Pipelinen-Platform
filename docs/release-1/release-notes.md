# Release 1 candidate notes

Status: **candidate, not released.** No `Release1` tag exists, and nothing here claims stakeholder acceptance. The [tag checklist](tag-checklist.md) lists what must be true before the tag is created.

Release 1 is the first complete local vertical slice of the Industrial Data Pipeline Platform: build a pipeline visually, validate it, preview data, run it, inspect the results, save it, reopen it and run it again, without editing source code.

## Install

See the [candidate guide](candidate.md). In short:

```bash
cp .env.example .env
python3 scripts/release_candidate.py start
python3 scripts/release_candidate.py demo
```

## What the candidate does

| Capability | Delivered in |
|---|---|
| Local projects with private data folders | [#63](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/63), [#83](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/83) |
| Portable pipeline JSON, DAG and configuration validation | [#61](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/61), [#65](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/65), [#81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81) |
| Visual builder, schema-driven block configuration | [#64](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/64), [#66](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/66), [#89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89) |
| CSV, JSON, Parquet and read-only SQLite sources; CSV and Parquet sinks | [#69](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/69), [#78](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/78) |
| Transforms (Select, Rename, Filter, Cast, Sort, Join, Aggregate, Null handling) and data-quality gates | [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72), [#71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71) |
| Local DAG executor with row and cell budgets | [#67](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/67), [#70](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/70), [#93](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/93) |
| Bounded selected-node preview | [#83](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/83) |
| Manual and timer runs, durable run history, block timings, row counts and logs | [#74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74), [#76](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/76), [#82](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/82) |
| Governed Parquet output inspection, 50 rows per page | [#77](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/77), [#89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89) |
| Security boundaries: loopback-only services, workspace containment, secret-free configuration | [#88](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/88) |
| End-to-end integration matrix and API contract tests | [#85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) |
| Measured workloads | [#90](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/90) |
| Packaged candidate: install, demo data, backup, restore, reset, CI rehearsal | Issue [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) |

## Known limitations

- **Single user, single machine.** There are no accounts. Both services listen on `127.0.0.1` only and are not meant to be exposed on a network.
- **Runs are synchronous.** The browser waits for a run to finish and gives up after five minutes. A run that outlasts that keeps going; check run history. The API itself sets no wall-clock limit on a run.
- **Measured capacity is small.** The largest measured workload is 3,000 rows × 26 columns ([#35 results](../performance/issue-35-workloads.md)). That is an observation, not a guaranteed capacity. Row and cell budgets do not bound bytes or many-to-many join growth.
- **Preview covers sources and simple transforms.** Join, Aggregate and Sort nodes are not previewed.
- **Output inspection reads Parquet only,** at most 500 rows and 100 columns per request. Values must be text, whole numbers, decimals or true/false; dates, timestamps and fixed-point decimals cannot be inspected yet.
- **SQL sources read local SQLite files only,** read-only.
- **No automatic downgrade.** An older candidate cannot open data after a newer one has upgraded it. Back up before upgrading; see [rollback and data compatibility](candidate.md#rollback-and-data-compatibility).

## Upgrade and rollback

Back up, check out the new revision, then `start`. The API upgrades the database on start. To roll back, check out the older revision and `restore` a backup that it created.

## Verification

The candidate's install, demonstration scenario, persistence, backup, reset and restore are rehearsed by the "Release candidate rehearsal" CI job. See the [#36 verification record](../testing/issue-36-release-candidate.md) for the commands, revisions and observed results.
