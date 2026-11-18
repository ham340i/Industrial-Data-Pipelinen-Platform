# Release 1 Acceptance

Status: checked against release candidate `5d05187` on November 17, 2026. 33 of 35 items have evidence; release documentation and the stakeholder demonstration remain.

Tracker: [GitHub issue #38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38).

Check an item only with evidence for the release candidate: commit, environment, command/scenario, observed outcome and accessible evidence link. A foundation API test or merged PR alone does not establish Release 1 acceptance. Environments: the clean install and recording ran on Ubuntu 24.04 with Docker 29.9.2 ([install record](../testing/release-1-clean-install.md)); the test evidence is the CI run on the same commit.

- [x] Application starts locally: `start` on a clean machine, both health checks ([install record](../testing/release-1-clean-install.md))
- [x] Project can be created: `demo` created "Release 1 demo"; also created through the UI in [author-preview-execute.spec.ts](../../frontend/release-tests/author-preview-execute.spec.ts) in CI
- [x] Project can be reopened: Reopened through the UI in the [recording](../demos/release-1-candidate-demo.webm) and after `restore` ([install record](../testing/release-1-clean-install.md))
- [x] Block library is visible: [block-library.spec.ts](../../frontend/standalone-tests/block-library.spec.ts), Standalone workspace smoke on Ubuntu and Windows ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Blocks can be added to canvas: [author-preview-execute.spec.ts](../../frontend/release-tests/author-preview-execute.spec.ts) adds all seven blocks ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Blocks can be connected: Same test connects six edges ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Blocks can be configured: Same test fills every block form; [configuration.spec.ts](../../frontend/standalone-tests/configuration.spec.ts)
- [x] Pipeline can be saved: Saved by `demo` and by the UI in the end-to-end test
- [x] Pipeline can be reloaded: Reopened by name in the [recording](../demos/release-1-candidate-demo.webm) and in the end-to-end test after a page reload
- [x] Invalid graph is rejected: [validation.spec.ts](../../frontend/standalone-tests/validation.spec.ts) and `tests/test_validation.py` ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Invalid configuration is rejected: [configuration.spec.ts](../../frontend/standalone-tests/configuration.spec.ts) and `tests/test_validation.py` ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Preview works: CSV source preview, 6 sampled rows, in the [recording](../demos/release-1-candidate-demo.webm)
- [x] CSV source works: Demo pipeline reads the sensor CSV; every block row count checked by `demo`
- [x] SQL source works: Demo pipeline reads the asset labels from SQLite; row count checked
- [x] Schema validation works: Validate Schema block in the demo pipeline
- [x] Filter works: Filter `reading > 10` in the demo pipeline; row count checked
- [x] Join works: Join of readings and labels in the demo pipeline
- [x] Aggregate works: Sum per label: `A = 30`, `B = 50`
- [x] Parquet output works: Published Parquet artifact queried after the run and after `restore`
- [x] Production DAG executor works: Two demo runs succeeded; rehearsal `outcome: passed` ([report](../testing/release-1-clean-install-rehearsal.json))
- [x] Run status is recorded: Run history in the [recording](../demos/release-1-candidate-demo.webm); runs survive restore
- [x] Block status is recorded: Per-block state in run monitoring ([recording](../demos/release-1-candidate-demo.webm))
- [x] Block timing is recorded: Per-block timings in run monitoring ([recording](../demos/release-1-candidate-demo.webm))
- [x] Row counts are available: Every block's row counts checked by `demo`
- [x] Logs are available: Run log events in the [recording](../demos/release-1-candidate-demo.webm)
- [x] Failures identify useful context: End-to-end test breaks the SQL query, sees `sql_query_failed` and opens the failed block from the error ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Output can be inspected/queried: Parquet output rows shown in the [recording](../demos/release-1-candidate-demo.webm)
- [x] Pipeline can be rerun without source changes: Rerun from the UI in the [recording](../demos/release-1-candidate-demo.webm) gave the same rows
- [x] Unit tests pass: Backend and frontend checks ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Integration tests pass: Backend integration matrix and Compose smoke ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] End-to-end tests pass: Release acceptance Playwright tests on Ubuntu and Windows ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] CI passes: Every job on `5d05187`, including "Release candidate rehearsal" ([CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873))
- [x] Installation documentation verified: [candidate.md](candidate.md) followed on a second machine ([install record](../testing/release-1-clean-install.md))
- [ ] Release documentation complete: release notes and the Wiki are updated in [#110](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/110), which still needs a teammate's approval
- [ ] Stakeholder demonstration completed: not yet; status recorded on [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38)

## Evidence

- Clean install, backup, reset, restore and rehearsal: [install record](../testing/release-1-clean-install.md)
- Demonstration recording: [release-1-candidate-demo.webm](../demos/release-1-candidate-demo.webm)
- CI on `5d05187`: [run 44171669873](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873)
- Stakeholder feedback: none yet ([#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38))
