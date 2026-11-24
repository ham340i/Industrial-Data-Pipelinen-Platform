# Release 2 team work allocation

Assigned by the team lead (ham340i) on November 24, 2026. Every student owns one story per Release 2 iteration, so each iteration has individual evidence, and each owner has a fixed reviewer who is not the author. Each student's four stories build one feature from first slice to hardening. Story points: 18 each (Iteration 5 stories are 3 points because the iteration is one week), 20 for ham340i who also runs the release.

| Student | Iteration 5 (Dec 1) | Iteration 6 (Dec 15) | Iteration 7 (Jan 19) | Iteration 8 (Feb 5) | Reviewer |
|---|---|---|---|---|---|
| ham340i (Ahmad) | [#121](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/121) Run Select, Rename and Filter on frames without Table conversions | [#133](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/133) Make file sources, sinks and relational blocks frame-native | [#134](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/134) Fuse chains of frame-native blocks into one lazy plan | [#122](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/122) Show pipeline revision history, compare revisions and restore one | @menaboulus |
| aboudka2003 (Aboud) | [#135](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/135) Configure a PostgreSQL connection by secret reference and test it | [#123](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/123) Read tables and SELECT queries from PostgreSQL as a source block | [#136](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/136) Configure the PostgreSQL source and test its connection from the builder | [#137](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/137) Recover from PostgreSQL failures during scheduled and manual runs | @adamoug |
| adamoug (Adam) | [#138](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/138) Parse and type-check safe column expressions | [#124](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/124) Add a Derived Column block that evaluates safe expressions | [#139](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/139) Combine tables with Union and remove duplicate rows with Deduplicate | [#140](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/140) Security review and tests for expressions, PostgreSQL and output queries | @Al-Yousef |
| Al-Yousef | [#130](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/130) Bring configuration form functions within the complexity limit | [#125](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/125) Evaluate range, pattern, allowed-value and uniqueness quality rules | [#141](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/141) Show a quality report for each run | [#142](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/142) Author quality rules in the builder with inline validation | @MarcElHaddad1 |
| joedaswagger (Joseph) | [#143](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/143) Bring run, pipeline and workspace controls within the complexity limit | [#126](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/126) Profile each column in a preview | [#144](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/144) Show the column profile in the preview panel | [#145](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/145) Connect and disconnect blocks with the keyboard | @aboudka2003 |
| karimikhaeil (Karim) | [#146](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/146) Benchmark harness for Release 2 execution changes | [#127](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/127) Compare two runs of a pipeline block by block | [#147](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/147) Show duration trends and flag slow runs | [#148](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/148) Release 2 performance report: Table path vs frame-native vs lazy | @joedaswagger |
| MarcElHaddad1 (Marc) | [#149](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/149) Define and validate structured output queries | [#128](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/128) Run structured filter, sort and group queries on Parquet outputs | [#150](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/150) Query builder and CSV export in output inspection | [#151](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/151) Deploy the Release 2 candidate to alpha testers and record the release | @karimikhaeil |
| menaboulus (Mena) | [#152](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/152) Store schedules and calculate their next run time | [#129](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/129) Run schedules in the background and recover them after restart | [#153](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/153) Manage schedules from the workbench | [#154](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/154) Release 2 acceptance test across the new features | @ham340i |

Issue [#131](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/131) (AI declarations) is coordinated by ham340i; each author fixes their own files and PRs.

GeorgesOgeil and PenguKev contributed in Release 1 (#88, #84) but are not on the Release 2 roster and have no Release 2 stories.

Every story follows the Release 1 format: story statement, owner, reviewer, points, ideal hours, priority, risk, feature label, milestone, acceptance criteria, dependencies, test requirements and stakeholder signoff.

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
