# RELEASE 1 SETUP REPORT

## 1. GitHub Changes Made

Created 34 future engineering items (17 user stories, 13 technical tasks, 4 spikes) plus one unassigned acceptance tracker. Reused existing milestones and management labels; added Release 1 feature categories and `release:1`. Each work item has one primary student and a distinct planned student reviewer. Existing issue #2, PR #3, Dependabot PR #1, branches and invitations were preserved. No application implementation, completed work, student contributions or approvals are claimed.

Live verification passed: 34 correct student assignments, 98 native blocking relationships, matching metadata and zero professor engineering assignments/review requests. The documentation and plan checks are delivered in [PR #39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39), stacked on compliance PR #3; both require independent review before main.

## 2. Milestones Created

No duplicate milestones created: all four were already present and were verified/reused.

| Milestone | Due Date | Estimated Work Items (Stories / Tasks / Spikes) | Total SP | Estimated Primary Hours |
|---|---|---|---:|---:|
| [Iteration 1](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestone/1) | 2026-10-06 | 10 (0 / 7 / 3) | 58 | 116 |
| [Iteration 2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestone/2) | 2026-10-20 | 8 (8 / 0 / 0) | 55 | 118 |
| [Iteration 3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestone/3) | 2026-11-03 | 8 (7 / 1 / 0) | 61 | 138 |
| [Iteration 4 (Release 1)](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestone/4) | 2026-11-17 | 8 (2 / 5 / 1) | 58 | 122 |

The separate acceptance tracker is in Iteration 4 with zero points/hours and no assignee; it is excluded from estimated-work counts. All estimates require team refinement.

## 3. Iteration 1

| Issue | Title | Primary Owner | Reviewer | SP | Ideal Hours | Priority | Risk | Dependencies |
|---|---|---|---|---:|---:|---|---|---|
| [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4) | Reproducible local workspace and Compose startup (task) | ham340i | aboudka2003 | 5 | 10 | Critical | Medium | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) |
| [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5) | React 19 workbench shell and typed API client (task) | aboudka2003 | adamoug | 5 | 10 | Critical | Medium | None |
| [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) | FastAPI shell with typed health and error contracts (task) | adamoug | Al-Yousef | 5 | 10 | Critical | Medium | None |
| [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7) | SQLite metadata models and migration foundation (task) | Al-Yousef | joedaswagger | 8 | 16 | High | High | [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) |
| [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) | Versioned Block SDK and typed registry contract (task) | joedaswagger | karimikhaeil | 8 | 16 | Critical | High | None |
| [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) | Portable pipeline JSON and DAG topology model (task) | karimikhaeil | MarcElHaddad1 | 5 | 10 | Critical | High | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) |
| [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) | Prove CSV to Select Columns to Parquet without the UI (spike) | MarcElHaddad1 | menaboulus | 8 | 16 | Critical | High | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) |
| [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11) | Application test harnesses and real stack CI gates (task) | menaboulus | ham340i | 8 | 16 | Critical | Medium | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) |
| [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12) | Spike approved data contracts and safe SQL connectivity (spike) | adamoug | Al-Yousef | 3 | 6 | Critical | High | None |
| [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13) | Spike Polars Arrow schema and memory behavior (spike) | karimikhaeil | MarcElHaddad1 | 3 | 6 | High | High | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) |

## 4. Iteration 2

| Issue | Title | Primary Owner | Reviewer | SP | Ideal Hours | Priority | Risk | Dependencies |
|---|---|---|---|---:|---:|---|---|---|
| [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14) | Save and reload portable pipelines in the workbench (story) | ham340i | adamoug | 8 | 16 | Critical | High | [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#19](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/19) |
| [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15) | React Flow canvas and discoverable block library (story) | aboudka2003 | Al-Yousef | 8 | 20 | Critical | High | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) |
| [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16) | CSV JSON and Parquet source blocks (story) | adamoug | joedaswagger | 5 | 12 | High | Medium | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) |
| [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17) | Schema-driven block configuration panel (story) | Al-Yousef | karimikhaeil | 8 | 16 | Critical | Medium | [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) |
| [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18) | Select Rename Filter and Cast transform blocks (story) | joedaswagger | MarcElHaddad1 | 8 | 16 | High | Medium | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) |
| [#19](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/19) | Create list and open local projects (story) | karimikhaeil | menaboulus | 5 | 12 | High | Medium | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7) |
| [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20) | Parquet and CSV sink blocks (story) | MarcElHaddad1 | ham340i | 5 | 10 | High | Medium | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) |
| [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21) | Validate graph ports and required configuration before run (story) | menaboulus | aboudka2003 | 8 | 16 | Critical | High | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15) |

## 5. Iteration 3

| Issue | Title | Primary Owner | Reviewer | SP | Ideal Hours | Priority | Risk | Dependencies |
|---|---|---|---|---:|---:|---|---|---|
| [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22) | Production local DAG executor and Polars context (task) | ham340i | Al-Yousef | 8 | 20 | Critical | High | [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21), [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16), [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18), [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20) |
| [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) | Read-only SQL source with secret references (story) | aboudka2003 | joedaswagger | 8 | 16 | Critical | High | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16) |
| [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24) | Join Aggregate and Sort transform blocks (story) | adamoug | karimikhaeil | 8 | 20 | Critical | High | [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13) |
| [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25) | Null handling and data-quality validation blocks (story) | Al-Yousef | MarcElHaddad1 | 8 | 16 | Critical | High | [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13) |
| [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26) | Bounded selected-node preview with schema and samples (story) | joedaswagger | menaboulus | 8 | 18 | High | High | [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25) |
| [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27) | Persist run telemetry and expose status/details APIs (story) | karimikhaeil | ham340i | 8 | 18 | Critical | Medium | [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7) |
| [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28) | Govern Parquet artifacts and query them with DuckDB (story) | MarcElHaddad1 | aboudka2003 | 8 | 18 | High | High | [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20), [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13), [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22) |
| [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) | Manual and bounded timer triggers with execute API (story) | menaboulus | adamoug | 5 | 12 | High | Medium | [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14) |

## 6. Iteration 4 / Release 1

| Issue | Title | Primary Owner | Reviewer | SP | Ideal Hours | Priority | Risk | Dependencies |
|---|---|---|---|---:|---:|---|---|---|
| [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30) | Run monitoring UI with block state and logs (story) | ham340i | joedaswagger | 8 | 16 | Critical | Medium | [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15) |
| [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) | Integrate author preview execute workflow with Playwright (task) | aboudka2003 | karimikhaeil | 8 | 18 | Critical | High | [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29), [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30), [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) |
| [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | Harden file SQL and configuration security boundaries (task) | adamoug | MarcElHaddad1 | 5 | 12 | Critical | High | [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16) |
| [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) | Actionable validation preview and execution error UX (story) | Al-Yousef | menaboulus | 5 | 12 | High | Medium | [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17) |
| [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34) | Stabilize execution failures and output cleanup (task) | joedaswagger | ham340i | 8 | 16 | Critical | High | [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) |
| [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) | Measure representative workloads and tune bounded execution (spike) | karimikhaeil | aboudka2003 | 8 | 16 | High | High | [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28) |
| [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) | Package and verify the local Release 1 candidate (task) | MarcElHaddad1 | adamoug | 8 | 16 | Critical | Medium | [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4), [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31), [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32), [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) |
| [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) | API engine block integration matrix and compatibility fixes (task) | menaboulus | Al-Yousef | 8 | 16 | Critical | High | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) |

## 7. Workload by Student

| Student | I1 SP | I2 SP | I3 SP | I4 SP | Total SP | Estimated Hours | Review Assignments | Review Hours | Total Including Review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ham340i | 5 | 8 | 8 | 8 | 29 | 62 | 4 | 8 | 70 |
| aboudka2003 | 5 | 8 | 8 | 8 | 29 | 64 | 4 | 8 | 72 |
| adamoug | 8 | 5 | 8 | 5 | 26 | 60 | 4 | 8 | 68 |
| Al-Yousef | 8 | 8 | 8 | 5 | 29 | 60 | 5 | 9 | 69 |
| joedaswagger | 8 | 8 | 8 | 8 | 32 | 66 | 4 | 8 | 74 |
| karimikhaeil | 8 | 5 | 8 | 8 | 29 | 62 | 4 | 8 | 70 |
| MarcElHaddad1 | 8 | 5 | 8 | 8 | 29 | 60 | 5 | 9 | 69 |
| menaboulus | 8 | 8 | 5 | 8 | 29 | 60 | 4 | 8 | 68 |

| Iteration | Work items | User stories / tasks / spikes | SP | Primary Hours | Review Hours | Total Hours |
|---|---:|---|---:|---:|---:|---:|
| 1 | 10 | 0 / 7 / 3 | 58 | 116 | 18 | 134 |
| 2 | 8 | 8 / 0 / 0 | 55 | 118 | 16 | 134 |
| 3 | 8 | 7 / 1 / 0 | 61 | 138 | 16 | 154 |
| 4 | 8 | 2 / 5 / 1 | 58 | 122 | 16 | 138 |

Total **232 SP / 494 primary hours + 66 reviewer hours = 560 planned hours**. See [balancing rationale](release-1-workload.md); no expertise or historical effort is invented.

## 8. Dependency Critical Path

[#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) → [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) → [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15) → [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21) → [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22) → [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27) → [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) → [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30) → [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) → [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) → [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38).

This dependency-weighted chain totals 162 ideal hours, not elapsed duration. Contract-first parallel work and capacity refinement are essential. See the [full graph](release-1-dependencies.md).

## 9. High-Risk Stories

[#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13), [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21), [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31), [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32), [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37).

Early risk work targets SDK/definitions, headless ETL, safe data/SQL contracts and Polars/Arrow semantics. Later high-risk work validates joins, execution, preview/query, security and integration; all are future work.

## 10. GitHub Project Status

**MANUAL ACTION REQUIRED:** Projects API lacks scope. No board or fields/views are claimed configured. Use [exact setup](GITHUB_PROJECT_SETUP.md) for **SOEN 490 - Industrial Data Pipeline Platform**, all requested views and real issue metadata. [CSV](planning/release-1-project-items.csv) is a field-entry aid.

## 11. Professor Access

**Professor Rodrigo Morales Alvarado (moar82) — academic reviewer, not engineering contributor.** His existing repository invitation is pending and was not modified or cancelled. Public repository content is visible; membership acceptance and Project sharing must be verified separately. No engineering ownership, points/hours or planned reviews are assigned to him.

## 12. Manual Actions Required

1. Review/merge compliance PR #3 first. Retarget planning PR #39 from `docs/2-soen490-compliance` to `main`, rerun/verify checks, and obtain independent student approval before merging. Do not merge into the compliance branch to bypass main protection.
2. Create/reuse and configure the Project through the browser or authorize Projects scope locally. Add all actual Release 1 issues, copy metadata and share with moar82.
3. Confirm each student's capacity, estimates and reviewer availability; refine/split oversized scope before starting.
4. Confirm the partner’s authorized representative, source/output contract, data/credential permissions and local hardware. Do not upload confidential inputs to GitHub.
5. Preserve the pending professor invitation; verify acceptance and Project/demo visibility.
6. Record real designs, implementations, tests, reviews and contribution evidence as work happens. Produce demos/tags only at actual completion.

## 13. Release 1 Readiness

Planning is executable: assigned work items, acceptance criteria, test requirements, dependencies, initial workload, target architecture and iteration evidence templates exist. The application, product dependencies, runnable product commands, real feature branches/PRs, product tests, benchmarks, demos and stakeholder acceptance remain to be produced by the students. Existing CI validates repository/planning integrity, not Release 1 acceptance.

All 19 distinct required block types are accounted for; Schema Validation / Validate Schema is one implementation. Manual and bounded Timer are included; REST and advanced industrial/distributed scope are excluded. No final tag was created.

## 14. First Actions for Every Student

| Student | One clear starting action |
|---|---|
| ham340i | [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4) — Draft the local directory/environment/Compose contract with shell owners, then implement integration after the shells exist. |
| aboudka2003 | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5) — Define the workbench shell routes and typed API-client contract, then scaffold the React application with a real smoke test. |
| adamoug | [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) — Draft the health/error response schemas and implement the FastAPI shell with API tests. |
| Al-Yousef | [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7) — Draft the minimal metadata relationships and migration strategy, then implement a tested SQLite migration. |
| joedaswagger | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) — Publish the typed Block SDK interface draft for early review, then prove it with a synthetic sample block. |
| karimikhaeil | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) — Draft versioned node/edge/port JSON with the SDK owner, then implement round-trip and cycle/order tests. |
| MarcElHaddad1 | [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) — Define the synthetic CSV fixture and golden Parquet output, then build the headless proof on the SDK/DAG contracts. |
| menaboulus | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11) — Agree real pytest/Vitest fixtures and gate commands with shell owners, then wire failing-check propagation into CI. |

## Planning verification evidence

[Live verification snapshot](planning/release-1-github-verification.json) records the checked issue IDs, owners, reviewers, milestones, estimates and native dependencies. All 35 new issues remain open. The professor's pending invitation was unchanged. No existing issues, milestones, branches, PRs or invitations were deleted or reassigned.

| Setup requirement | Result |
|---|---|
| Iterations 1–4 and exact dates | PASS — reused existing milestones 1–4 |
| Feature/supporting labels | PASS — 16 added; equivalent infrastructure/task labels reused |
| User stories / technical tasks / spikes | PASS — 17 / 13 / 4, plus unassigned acceptance tracker |
| Points, hours, priority, risk, criteria, tests and AI fields | PASS — present in all 34 work items |
| Student assignments | PASS — all eight own meaningful work in every iteration |
| Planned reviewers | PASS — distinct students, rotation and separate effort reserve |
| Professor workload | PASS — zero issue/PR engineering assignments and zero routine review requests |
| Native dependencies | PASS — 98 created; graph is acyclic |
| Workload | PASS — 26–32 SP and 60–66 primary hours per student; estimates need team confirmation |
| Project configuration | MANUAL ACTION REQUIRED — insufficient Projects scope; exact steps and metadata supplied |
| Professor Project sharing | MANUAL ACTION REQUIRED — verify visibility after board creation |
| PR/contribution/iteration/traceability material | PASS — updated and linked; completion evidence remains pending |
| Acceptance issue | PASS — #38, unassigned with zero implementation estimate |
| Local plan validation | PASS — roster, ownership, estimates, milestones and dependency checks |
| Repository and documentation checks | PASS — current sources and maintained links validated |
| Tool regression tests | PASS — 14 tests, including professor-assignment and dependency-cycle rejection |
| Application acceptance / benchmarks / release tags | NOT RUN / NOT CREATED — this is planning, not product completion |

Run `python3 scripts/check_release_plan.py`, `python3 scripts/check_repository.py`, `python3 scripts/check_docs.py` and `python3 -m unittest discover -s scripts/tests -v` from the repository root. Current commands verify the planning/repository tooling only.

### Published planning revision

Commit `ff1b8f6` passed [Repository checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36663929695), [Documentation checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36663929702), and the existing SonarCloud check. These validate repository/planning changes only. See [PR #39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39) for the latest revision’s checks and review state; no human approval is claimed.
