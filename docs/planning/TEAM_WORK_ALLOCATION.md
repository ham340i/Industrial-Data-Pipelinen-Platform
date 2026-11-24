# Release 2 team work allocation (proposal)

Proposed from each student's Release 1 work (see the [Release 1 breakdown](../releases/iteration-4-release-1.md#breakdown-by-individual)) and the roles in the Release 2 brief. Each student confirms their own row; issues are assigned only after that. Nothing here records work that has been done.

GeorgesOgeil and PenguKev contributed in Release 1 (#88, #84) but are not on the Release 2 roster in the brief. They are left unassigned until the team confirms their status.

| Student | Feature stories | Supporting work | Points / ideal hours | Depends on | Deliverables | Required tests | Reviews |
|---|---|---|---|---|---|---|---|
| ham340i (Ahmad) | F1 lazy execution, F2 revision history | Release 1 tag and Release, scope review, Wiki architecture, release management | 21 / 48 | Spike #109 | Lazy executor path; revision list, diff, restore | Eager vs lazy equality; memory benchmark; diff and restore tests | Reviews F9 |
| aboudka2003 (Aboud) | F3 PostgreSQL source | Frontend wiring for new source config | 8 / 20 | Secret policy | Connector, config schema, preview support | Auth failure, timeout, non-SELECT rejection, type mapping | Reviews F6 |
| adamoug (Adam) | F4 derived column, Union, Deduplicate | Security review of F3 and F8 | 8 / 20 | Block SDK | Three transform blocks | Golden outputs; invalid expression; schema mismatch | Reviews F3 |
| Al-Yousef | F5 quality rules and report | Refactor `configuration/schema.ts` and `BlockConfigPanel` complexity | 8 / 20 + refactor | Quality blocks | Rule engine, run report, UI | Boundary, empty input, warn vs fail | Reviews F4 |
| joedaswagger (Joseph) | F6 preview profiling, keyboard connection | Refactor `RunControls`, `WorkspaceSettings`, `PipelineControls`; review #119 | 8 / 18 + refactor | Preview | Profile panel; keyboard connection | Row budget; keyboard-only browser test | Reviews F7 |
| karimikhaeil (Karim) | F7 run comparison and trends | Performance measurement of F1 | 5 / 14 | Run telemetry | Comparison API and UI | Fixtures with failed and slow runs | Reviews F2, F8 |
| MarcElHaddad1 (Marc) | F8 output query builder and CSV export | Alpha deployment, release notes, Dependabot #107 | 8 / 18 | Artifact query | Query builder, export | Server-side validation; row limit; empty result | Reviews F5 |
| menaboulus (Mena) | F9 persistent schedules | Release 2 acceptance test, CI upkeep | 8 / 20 | Triggers | Schedule store, scheduler, UI | Restart recovery; missed-run policy; overlap prevention | Reviews F1 |

Story points per student range from 5 to 21. ham340i carries more as the release lead; karimikhaeil's lower feature load is balanced by the F1 performance measurement.

## Contribution evidence status

| Student | Release 1 personal record | Release 2 record |
|---|---|---|
| ham340i | Iterations 1, 3, 4 | Not started |
| aboudka2003 | Iterations 1, 3, 4 | Not started |
| adamoug | Missing | Not started |
| Al-Yousef | Iterations 1 to 4 | Not started |
| joedaswagger | Iteration 1 | Not started |
| karimikhaeil | Iterations 1, 2, 4 | Not started |
| MarcElHaddad1 | Iteration 3 | Not started |
| menaboulus | Iterations 1, 4 | Not started |

Each student writes their own record in `docs/individual-contributions/` from the [template](../individual-contributions/TEMPLATE.md). Records, reflections and peer evaluations are not written for anyone else.
