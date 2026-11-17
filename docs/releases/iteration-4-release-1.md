# Release 1 notes (Iteration 4)

## Release 1 (Iterations 1 to 4), due November 17, 2026

### Overall summary

Release 1 delivers a working local ETL vertical slice: a user creates a project, draws a pipeline from file, SQL, transform, data-quality and sink blocks, validates it, previews a step, runs it manually or on a timer, watches block-level run evidence and queries the governed Parquet output, and that whole workflow is exercised end to end in Playwright. The file, SQL and configuration boundaries were hardened against adversarial probes, and representative synthetic workloads were measured. 33 of 34 planned items are closed (224 of 232 points), with 1,109 backend and 226 frontend tests passing in CI. Release packaging (#36) remains open, and no stakeholder signoff is recorded yet.

### Velocity

| Iteration | Due | Planned points | Completed points | Planned ideal hours | Notes |
|---|---|---:|---:|---:|---|
| 1 Foundation and architecture | Oct 6 | 58 | 58 | 116 | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10) and [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13) were closed one to two weeks late |
| 2 Visual pipeline builder | Oct 20 | 55 | 55 | 118 | All items closed Oct 21 to 22 |
| 3 Execution engine and data processing | Nov 3 | 61 | 61 | 138 | [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26) and [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28) closed Nov 11 |
| 4 Integration, quality and release | Nov 17 | 58 | 50 | 122 | [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31), [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32), [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34) and [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) closed on the due date; [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) open |
| **Release 1** | | **232** | **224 (97%)** | **494** | |

Average velocity over the three completed iterations is 58 points per two-week iteration for the team.

**Did we accomplish what we planned?** Almost. Every product feature and the security and performance work were delivered; what slipped is release packaging ([#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36)) and the acceptance record ([#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38)). The cause is visible in the dates: Iteration 1 and 3 items finishing late pushed four Iteration 4 items to the final day. Nothing was finished early.

### Contractor estimate

Completed work corresponds to 478 planned ideal engineering hours (the ideal hours of the closed items), plus the planned review reserve of 2 hours per item. Actual hours were not tracked.

Estimated charge = ideal hours of completed work x hourly rate. The team has not yet agreed the rate to use, so no dollar figure is stated here; it must be added with its source.

### Retrospective

The team has not held and recorded a retrospective. The points below are observations from the repository history, offered as input to that discussion.

**What went well**

- A headless end-to-end proof in Iteration 1 removed the largest technical risk before any UI depended on the engine.
- Reviews that examined the code found real defects before merge, for example [#74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74), [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72), [#59](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/59) and [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52).
- CI was in place from the first week and every merge used a merge commit, so history and authorship are intact.

**What went wrong**

- Fewer than half of the feature and fix pull requests received a review with a specific technical comment; many approvals had no comment.
- Items were closed after their iteration date in every iteration, which compressed integration.
- Course evidence lagged the code: no meeting minutes, no stakeholder signoff, no licence decision, no release tag, and AI declarations missing from most source files and pull requests.
- Individual contribution records are incomplete for several people.

**What we will change**

- Every approval states what was checked; the reviewer named on the issue is requested when the pull request opens.
- An item is closed only when its pull request is merged and its evidence is linked.
- Minutes, AI declarations and contribution records are part of the definition of done and are checked at each iteration boundary.

### Open items

| Item | Owner | State |
|---|---|---|
| [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) Package and verify the Release 1 candidate | MarcElHaddad1 | No pull request |
| [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38) Release 1 acceptance | Team | Needs stakeholder review |

### Breakdown by individual

Evidence drawn from GitHub at Release 1. Each contributor adds their own description in their [personal record](../individual-contributions/README.md); a contributor with no description and no commits receives zero for the release.

| Contributor | Closed items owned | Open items owned | Merged pull requests authored | Pull requests reviewed |
|---|---|---|---|---|
| aboudka2003 | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) | None recorded | [#43](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/43), [#78](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/78), [#89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89) | [#45](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/45), [#65](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/65), [#77](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/77) |
| adamoug | [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6), [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16), [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24) | [#92](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/92) | [#44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44), [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52), [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72) | [#46](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/46), [#51](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/51), [#55](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/55), [#76](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/76) |
| Al-Yousef | [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25), [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33), [#49](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/49), [#50](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/50), [#54](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/54), [#80](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/80) | None recorded | [#48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48), [#51](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/51), [#53](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/53), [#55](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/55), [#66](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/66), [#69](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/69), [#71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71), [#75](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/75), [#81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81) | [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52), [#70](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/70), [#85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) |
| GeorgesOgeil | [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | None recorded | [#88](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/88) | None recorded |
| ham340i | [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30) | None recorded | [#3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3), [#39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39), [#40](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/40), [#41](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/41), [#42](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/42), [#45](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/45), [#47](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/47), [#64](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/64), [#67](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/67), [#70](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/70), [#82](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/82) | [#53](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/53), [#57](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/57), [#66](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/66), [#69](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/69), [#74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74) |
| joedaswagger | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34) | None recorded | [#59](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/59), [#83](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/83), [#86](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/86), [#93](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/93) | [#48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48), [#82](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/82) |
| karimikhaeil | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13), [#19](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/19), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) | [#91](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/91) | [#61](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/61), [#62](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/62), [#63](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/63), [#90](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/90) | [#59](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/59), [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72) |
| MarcElHaddad1 | [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28) | [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) | [#77](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/77) | [#71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71), [#75](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/75) |
| menaboulus | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11), [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21), [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37), [#87](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/87) | None recorded | [#46](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/46), [#65](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/65), [#74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74), [#76](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/76), [#85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) | [#1](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/1), [#3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3), [#39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39), [#40](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/40), [#41](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/41), [#42](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/42), [#43](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/43), [#44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44), [#47](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/47), [#59](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/59), [#60](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/60), [#61](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/61), [#62](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/62), [#63](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/63), [#64](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/64), [#67](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/67), [#78](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/78), [#81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81), [#83](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/83), [#84](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/84), [#86](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/86), [#89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89), [#90](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/90) |
| PenguKev | None recorded | None recorded | [#84](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/84) | [#85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) |

Personal records present at Release 1: Al-Yousef (Iterations 1 to 4), ham340i (1, 3, 4), karimikhaeil (1, 2, 4), aboudka2003 (1, 3, 4), menaboulus (1, 4), joedaswagger (1), MarcElHaddad1 (3). Missing entirely: adamoug, GeorgesOgeil, PenguKev.

## Per-iteration records

Planning tables, demo scripts and testing evidence for each iteration: [Iteration 1](../iterations/iteration-1/README.md), [Iteration 2](../iterations/iteration-2/README.md), [Iteration 3](../iterations/iteration-3/README.md), [Iteration 4 and Release 1](../iterations/iteration-4-release-1/README.md).

## Release tags

| Release | Tag | GitHub Release | Demo video |
|---|---|---|---|
| Release 1 | Not created yet (`v1.0.0-release1` planned) | Not created yet | Not recorded yet |
