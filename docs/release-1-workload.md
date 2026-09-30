# Release 1 workload

Exactly eight student contributors. `moar82` is excluded from ownership, review, points and hours. `MarcElHaddad1` is GitHub’s canonical capitalization of the supplied MarcelHaddad1 account.

Initial estimates for future work, not actual time or student contribution claims. Primary ideal hours include design, implementation, tests and documentation; reviewer hours are separate. The acceptance tracker is unassigned and zero-estimate so it does not duplicate delivery work. Existing repository setup issue #2 is excluded from this new product workload.

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

## Iteration totals

| Iteration | Work items | User stories / tasks / spikes | SP | Primary Hours | Review Hours | Total Hours |
|---|---:|---|---:|---:|---:|---:|
| 1 | 10 | 0 / 7 / 3 | 58 | 116 | 18 | 134 |
| 2 | 8 | 8 / 0 / 0 | 55 | 118 | 16 | 134 |
| 3 | 8 | 7 / 1 / 0 | 61 | 138 | 16 | 154 |
| 4 | 8 | 2 / 5 / 1 | 58 | 122 | 16 | 138 |


Total: **232 SP; 494 primary ideal hours; 66 review hours; 560 hours including review.** These are planning estimates and must be reviewed against student availability. Iteration 1 requires roughly 12–19 hours per student including review in a short foundation window; flag capacity conflicts immediately.

## Allocation rationale

Only ham340i-attributed repository setup history was available. It supports continuity on local foundations, not an assumption of product expertise. Other students’ frontend/backend competence cannot be inferred from this repository. Allocation is therefore balanced and rotates across layers: UI owners take SQL/integration work, metadata owners take configuration/quality work, SDK owners take transforms/preview/engine hardening, and test-infrastructure owners implement validation/triggers/compatibility work.

Point totals range from 26 to 32; primary effort ranges from 60 to 66 hours. The difference reflects uncertain SDK/preview/engine boundaries and the sizes of decomposed tasks rather than student ability. Do not force equal points by adding fake work. Every student owns implementation/design and feature tests in all four iterations, and every student has at least four planned reviews. Cross-review knowledge sharing supplements the task rotation.

Re-estimate in refinement; if a story exceeds 13 SP, split it with a clear dependency and rebalance both primary and reviewer effort. Story points are not personal productivity scores. I3/I4 assignments provide release direction and are refined as the next-two-iteration commitment window moves.
