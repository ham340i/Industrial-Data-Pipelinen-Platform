# Iterations

No completed iteration evidence exists yet. Copy [iteration template](ITERATION_TEMPLATE.md) for an actual iteration; link issues, reviews, tests and individual contributions. Plan approximately **two iterations ahead**. Do not prepopulate future milestones with invented work.

## Course schedule

Dates supplied in the project brief; verify any course updates with the instructor. GitHub setup stores each listed calendar date at 23:59:59 UTC as a date marker, not an assertion about the course submission time zone.

| Milestone | Due date |
|---|---|
| Iteration 1 | 2026-10-06 |
| Iteration 2 | 2026-10-20 |
| Iteration 3 | 2026-11-03 |
| Iteration 4 (Release 1) | 2026-11-17 |
| Iteration 5 | 2026-12-01 |
| Iteration 6 | 2026-12-15 |
| Iteration 7 | 2027-01-19 |
| Iteration 8 (Release 2) | 2027-02-05 |
| Iteration 9 | 2027-02-16 |
| Iteration 10 | 2027-03-02 |
| Iteration 11 | 2027-03-16 |
| Iteration 12 | 2027-03-30 |
| Iteration 13 (Final Release / Release 3) | 2027-04-13 |

Final Group Presentation, Peer Evaluations and Stakeholder Feedback: **2027-04-13** (feedback due by this date).

## Completion tags

After actual completion and reviewed evidence, tag the reviewed main commit `Iteration1`, `Iteration2`, … `Iteration13`. Example only, run after confirming completion:

```sh
git tag -a Iteration1 -m "Iteration 1 completed" <reviewed-commit-sha>
git push origin Iteration1
```

Replace the placeholder with the verified SHA. Never move a published tag silently. Release iterations additionally use `Release1`, `Release2`, `Release3`; see [release process](../releases/README.md). No completion tags have been created by this setup.
