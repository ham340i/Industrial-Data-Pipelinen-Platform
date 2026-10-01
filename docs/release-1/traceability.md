# Release 1 Traceability

## Expected evidence chain

Requirement → GitHub Issue → Engineering Design → Assigned Developer → Feature Branch → Commits → Pull Request → Automated Tests → CI → Student Review → Merge to main → Iteration Tag → Iteration Evidence → Individual Contribution Record

Link actual design decisions, commits, reviews and evidence from each issue and its iteration record. Use the [existing traceability guide](../release-1-traceability.md), [iteration records](../iterations/README.md) and [individual contribution template](../individual-contributions/TEMPLATE.md).

## Current issue mapping

Snapshot: October 1, 2026. Requirements and iteration allocations come from the existing backlog; owners and issue/PR status were read from GitHub. No assignments were changed. Closed issues and merged PRs do not establish iteration acceptance. Unknown evidence remains explicitly unrecorded. Professor `moar82` has no engineering ownership.

| Requirement | Issue | Owner | Branch | PR | Tests | CI | Iteration | Status |
|-------------|-------|-------|--------|----|-------|----|-----------|--------|
| Reproducible local workspace and Compose startup | [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4) | ham340i | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| React 19 workbench shell and typed API client | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5) | aboudka2003 | `feature/5-workbench-shell` | [#43](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/43), open | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| FastAPI shell with typed health and error contracts | [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6) | adamoug | `FastAPI-shell` | [#44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44), merged | [API tests](../../tests/test_api.py); [local results](../testing/iteration-structure-validation.md) | Not recorded here | 1 | Issue closed; iteration acceptance not recorded |
| SQLite metadata models and migration foundation | [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7) | Al-Yousef | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Versioned Block SDK and typed registry contract | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) | joedaswagger | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Portable pipeline JSON and DAG topology model | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9) | karimikhaeil | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Prove CSV to Select Columns to Parquet without the UI | [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) | MarcElHaddad1 | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Application test harnesses and real stack CI gates | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11) | menaboulus | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Spike approved data contracts and safe SQL connectivity | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12) | adamoug | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Spike Polars Arrow schema and memory behavior | [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13) | karimikhaeil | Not recorded | Not recorded | Not recorded | Not recorded here | 1 | Issue open; acceptance not recorded |
| Save and reload portable pipelines in the workbench | [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14) | ham340i | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| React Flow canvas and discoverable block library | [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15) | aboudka2003 | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| CSV JSON and Parquet source blocks | [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16) | adamoug | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Schema-driven block configuration panel | [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17) | Al-Yousef | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Select Rename Filter and Cast transform blocks | [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18) | joedaswagger | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Create list and open local projects | [#19](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/19) | karimikhaeil | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Parquet and CSV sink blocks | [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20) | MarcElHaddad1 | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Validate graph ports and required configuration before run | [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21) | menaboulus | Not recorded | Not recorded | Not recorded | Not recorded here | 2 | Issue open; acceptance not recorded |
| Production local DAG executor and Polars context | [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22) | ham340i | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Read-only SQL source with secret references | [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) | aboudka2003 | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Join Aggregate and Sort transform blocks | [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24) | adamoug | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Null handling and data-quality validation blocks | [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25) | Al-Yousef | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Bounded selected-node preview with schema and samples | [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26) | joedaswagger | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Persist run telemetry and expose status/details APIs | [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27) | karimikhaeil | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Govern Parquet artifacts and query them with DuckDB | [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28) | MarcElHaddad1 | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Manual and bounded timer triggers with execute API | [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) | menaboulus | Not recorded | Not recorded | Not recorded | Not recorded here | 3 | Issue open; acceptance not recorded |
| Run monitoring UI with block state and logs | [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30) | ham340i | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Integrate author preview execute workflow with Playwright | [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) | aboudka2003 | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Harden file SQL and configuration security boundaries | [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | adamoug | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Actionable validation preview and execution error UX | [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) | Al-Yousef | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Stabilize execution failures and output cleanup | [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34) | joedaswagger | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Measure representative workloads and tune bounded execution | [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) | karimikhaeil | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Package and verify the local Release 1 candidate | [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) | MarcElHaddad1 | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| API engine block integration matrix and compatibility fixes | [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) | menaboulus | Not recorded | Not recorded | Not recorded | Not recorded here | 4 | Issue open; acceptance not recorded |
| Release 1 vertical slice acceptance | [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38) | Unassigned; tracker | Not recorded | Not recorded | Not recorded | Not recorded | 4 | Planned |

## Additional requirement template

| Requirement | Issue | Owner | Branch | PR | Tests | CI | Iteration | Status |
|-------------|-------|-------|--------|----|-------|----|-----------|--------|
| TODO requirement | TODO actual issue | TODO student | Not recorded | Not recorded | Not recorded | Not recorded | TODO | Planned |
