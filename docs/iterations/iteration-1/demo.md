# Iteration 1 Demonstration

Status: Not Yet Demonstrated. Prepared plan updated October 4, 2026; execution, attendees, video and feedback remain to be recorded.

## Demo Objective

Demonstrate the merged local workbench/API/Compose foundations and their failure handling. Add the smallest CSV → Select Columns → Parquet proof only after SDK #8, DAG #9 and reference-runner #10 are independently reviewed and integrated. This is the Iteration 1 foundation demo, not full Release 1 acceptance.

## Preconditions

- Use a clean checkout of the reviewed demonstration commit; record `git rev-parse HEAD` and `git status --short`.
- Record platform, Docker/Compose and browser versions. Use synthetic inputs and an isolated test volume.
- Review the [workspace lifecycle guide](../../local-workspace.md). Verify frontend/API ports are available; changing host ports must follow the guide.
- Use the [headless-proof issue](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) owner's exact commands and committed fixture once that implementation exists. Do not invent a runner command before its interface is delivered.
- Verify the evidence/video is accessible to the team/professor; confirm the authorized stakeholder representative separately.

## Startup Commands

From the repository root:

```sh
git rev-parse HEAD
git status --short
docker compose version
docker compose up --build --wait
docker compose ps
```

Open `http://127.0.0.1:3000` and `http://127.0.0.1:8000/docs`. Follow the workspace guide if ports were changed. The automated isolated stack check is `python scripts/smoke_workspace.py --browser` after installing the frontend browser-test dependencies as documented; it creates and cleans its own stack rather than validating an already running demonstration instance.

## Demonstration Steps

1. Show healthy real API and frontend services, then the Overview's connected API status. Open `/api/v1/health` and the generated OpenAPI contract.
2. Navigate with keyboard to Builder, create/edit the shell's in-memory draft and refresh a direct Builder link. Explain that this shell does not yet execute or persist an ETL graph.
3. Use OpenAPI's example endpoint with a valid synthetic payload, then an invalid payload. Record the versioned route, 422 error envelope and correlation header. Verify the single-header correction only after the #49 implementation is merged.
4. Stop the API with `docker compose stop api`, observe the frontend's error, restart it with `docker compose start api`, wait for health and retry. Record actual recovery, not just a successful command exit.
5. Link the real-service automated smoke evidence for proxy health, non-root services, persistence and isolated teardown. Its marker does not establish database migrations.
6. After metadata PR #48 merges, run its documented migration/persistence tests and explain immutable revisions versus private bindings using synthetic data. Record exact commands and results; do not imply project CRUD exists yet.
7. After #8/#9/#10 integrate, execute the owner's headless fixture command, read back Parquet and compare expected columns, rows and schema. Run the missing-column failure and explain its diagnostic. Record both outputs and the runner's prototype limits.
8. Finish with the [remaining owner checklist](../../team-readiness-2026-10-04.md#iteration-1-work-that-must-become-reviewable), actual feedback and any slipped scope.

## Expected Behavior

Real versioned health connects through the frontend proxy; navigation works; invalid requests return safe errors; offline/recovery is visible. Conditional metadata/ETL segments must meet their issue acceptance tests on the demonstrated revision. Expected behavior is not an observed pass.

## Actual Observed Behavior

Not recorded. During execution record each step's actual result, failures, environment, commit and accessible evidence. Keep conditional segments marked Not Demonstrated if their PRs have not merged.

## Known Limitations

Main currently lacks the SDK/DAG/headless ETL implementation. Metadata PR #48 and integration correction #49 are pending independent review. Graph authoring/configuration, project/pipeline save-reload, production execution, preview, telemetry and governed outputs remain assigned future product work. No stakeholder approval or complete Release 1 behavior is asserted.

## Issues Demonstrated

Planned foundation scope: #4/#5/#6/#11. Conditional segments: #7/#8/#9/#10 and the #49 correction. Actual demonstrated issues: not yet recorded.

## Evidence

Preparation/evidence sources: [team audit](../../team-readiness-2026-10-04.md), [testing evidence](testing-evidence.md), [workspace verification](../../testing/issue-4-local-workspace.md), [frontend verification](../../testing/issue-5-workbench.md) and [harness verification](../../testing/issue-11-test-harnesses-ci.md).

Demonstration commit, attendees/date, video/screenshots, raw result links and authorized feedback: not recorded. No iteration tag is created by preparing this plan. Normal teardown: `docker compose down`; explicit reset deletes data and must follow the workspace guide.

AI assistance: Codex prepared this plan from current implementation/docs at Al-Yousef's request. No actual demonstration, personal contribution or stakeholder signoff is invented.
