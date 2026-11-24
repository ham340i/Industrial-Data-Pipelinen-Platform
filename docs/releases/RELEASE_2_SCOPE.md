# Release 2 scope (proposal)

**Status: stories created and assigned on November 24, 2026 (#121 to #154); scope approval by the stakeholder representative is still to be recorded.** The original Project Overview is not in the repository, so this scope is built from the sources below. It becomes the Release 2 scope when the team agrees and the stakeholder representative (ham340i, for Taconics) approves it at the Iteration 5 scope review recorded in the [Release 1 signoff](../stakeholder/release-1-signoff.md).

Release 2 runs over Iterations 5 to 8 (due December 1, December 15, January 19 and February 5).

## Sources used

| Source | What it says about Release 2 |
|---|---|
| [Release 1 plan](../release-1-plan.md) | Release 1 excluded advanced scheduling, REST and streaming connectors, distributed execution, enterprise identity and the remaining transform categories |
| Spike [#109](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/109) decision | Move to frame-native blocks and lazy sources before fusing plans |
| [Diversity statement](../wiki/Diversity-Statement.md) | Keyboard alternative for connecting blocks and French text are Release 2 candidates |
| Release 1 presentation | "Release 2: frame-native blocks, lazy sources, deployment for testers" |
| Release 2 brief from the team | Lists candidate capabilities: scheduling, advanced connectors, reusable pipelines, versioning, advanced error handling, performance |
| Code Quality Rubric | Exceptional needs at least 8 substantive features and at least 85% of planned stories done |

## Conflicts that need a decision

1. **Roster.** The brief lists 8 students; GitHub shows 10 contributors (GeorgesOgeil and PenguKev merged #88 and #84). The plan below assigns the 8 named students and leaves GeorgesOgeil and PenguKev unassigned until confirmed.
2. **Counting features.** The rubric does not say whether Release 1 features count toward Release 2. The plan assumes they do not and plans 9 new substantive features, so 8 finished is 89%.
3. **Connectors.** The brief mentions "advanced connectors". Kafka, MQTT and OPC UA need infrastructure the team has not set up. This proposal takes PostgreSQL (read-only) for Release 2 and leaves streaming connectors to Release 3.
4. **Partner name.** Repository documents name Pratt & Whitney Canada; the stakeholder is Taconics. Documents need correcting once the exact name is confirmed.

## Planned substantive features (9)

Each feature meets at least two of the rubric's substantive conditions, shown in the last column.

| ID | Feature | Acceptance criteria (summary) | Depends on | Proposed owner | Points / ideal hours | Substantive because |
|---|---|---|---|---|---|---|
| F1 | **Lazy frame-native execution** for file sources and row-wise transforms | Executor builds one lazy plan per chain of compatible blocks and collects at sinks or breakpoints; outputs identical to eager mode on the golden datasets; peak memory below eager on the 2M-row workload; falls back to eager per block with a logged reason | Spike #109 | ham340i | 13 / 30 | algorithmic processing; coordinates engine, blocks and telemetry |
| F2 | **Pipeline revision history and restore** | List saved revisions with author time and change summary; show which nodes, edges and settings changed between two revisions; restore an old revision as a new revision; runs keep pointing at their own revision | Existing immutable revisions | ham340i | 8 / 18 | state transition; comparison algorithm |
| F3 | **Read-only PostgreSQL source** with secret references | Connects through a secret reference, never a stored password; only single SELECT statements; row and time limits; typed columns; clear errors for auth, network and timeout; works in preview and execution | Secret policy (#32) | aboudka2003 | 8 / 20 | external service with result transformation; validation rules |
| F4 | **Derived-column and Union/Deduplicate transforms** | Expressions from a safe whitelist (arithmetic, comparisons, string and date functions) with type checking; Union checks schema compatibility; Deduplicate on chosen keys with keep-first/last | Block SDK | adamoug | 8 / 20 | data transformation; validation rules |
| F5 | **Rule-based data-quality checks with a run quality report** | Range, pattern, allowed-values and uniqueness rules; per-rule pass/fail counts and sample failing rows in run results; a rule can warn or fail the run | Quality blocks (#25) | Al-Yousef | 8 / 20 | business rules; aggregation of results |
| F6 | **Column profiling in preview** and **keyboard block connection** | Preview shows per-column null count, min, max and distinct estimate within the existing row budget; blocks can be connected without a mouse, announced to screen readers | Preview (#26) | joedaswagger | 8 / 18 | calculation; multi-step UI workflow |
| F7 | **Run comparison and performance trends** | Compare two runs of a pipeline: duration, rows in/out per block, status changes; trend of duration over the last N runs; flag a run more than 50% slower than the median | Run telemetry (#27) | karimikhaeil | 5 / 14 | aggregation and calculation; coordinates telemetry and UI |
| F8 | **Output query builder and CSV export** | Filter, sort, choose columns and group/aggregate a Parquet output from the UI; validated server-side before DuckDB runs; export the result as CSV within a row limit | Artifact query (#28) | MarcElHaddad1 | 8 / 18 | validation rules; data aggregation |
| F9 | **Persistent recurring schedules** | Cron-style schedules saved in SQLite; survive API restart; a missed run is skipped or run once per a chosen policy; overlapping runs prevented; schedule list and next-run time in the UI | Triggers (#29) | menaboulus | 8 / 20 | background processing; state transitions |

Total: 74 points, 178 ideal hours, before the 2-hour review reserve per story.

## Supporting work (not counted as features)

| Work | Why | Owner |
|---|---|---|
| Close Release 1: merge #119, tag `Release1`, publish the GitHub Release | Rubric traceability check 12 and deployment record | ham340i |
| Frontend complexity refactor | Rubric structure checks 2 and 3 currently fail | Al-Yousef, joedaswagger |
| AI declarations on files and PRs | Rubric AI checks 3 and 4 currently fail | All |
| Stakeholder signoff label on accepted stories | Traceability check 7 | ham340i |
| Deployment for alpha testers (packaged installer on a tester workstation) | Release strategy and INV-3 user data | MarcElHaddad1 |
| LICENSE file | PR-1 and third-party attribution | Team decision |

## Deferred to Release 3

Kafka, MQTT and OPC UA connectors; REST ingestion; reusable sub-pipelines and templates; French interface; distributed execution; enterprise identity. Each needs infrastructure or a stakeholder decision that Release 2 does not have.

## Risks

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Iteration 7 spans the holiday break | High / high | Put backend cores in Iterations 5 and 6; Iteration 7 only integrates |
| Lazy execution changes results | Medium / high | Golden-output equality tests against eager mode before switching any block |
| PostgreSQL needs a test database | Medium / medium | Run PostgreSQL in a CI service container with synthetic data |
| Review rate stays near 42% | High / high | Reviewer named on every issue; no merge without a technical comment |
| Late Release 1 pattern repeats (work landing on the due date) | High / medium | Mid-iteration checkpoint; each story split so the backend lands first |
