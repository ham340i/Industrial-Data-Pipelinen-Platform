# Release 1

Status: Planned. Deadline: **November 17, 2026**.

## TARGET RELEASE 1 BEHAVIOR

Release 1 targets the first complete vertical slice. This workflow remains a target until demonstrated:

BUILD → CONFIGURE → VALIDATE → PREVIEW → EXECUTE → OBSERVE → SAVE → RELOAD → RERUN

1. Start the application locally.
2. Create or open a project.
3. Browse available blocks.
4. Drag blocks onto a visual canvas.
5. Connect blocks.
6. Configure blocks.
7. Validate graph topology and configuration.
8. Preview supported intermediate data.
9. Execute the target pipeline below.
10. Inspect run status, block status, block timings, row counts, logs and failures.
11. Inspect or query generated output.
12. Save the pipeline.
13. Reload the pipeline.
14. Execute it again without modifying application source code.

```text
CSV → Validate Schema → Filter ─┐
                               ├→ Join → Aggregate → Parquet
SQL Source ────────────────────┘
```

## Acceptance and evidence

Use the [acceptance checklist](acceptance.md), [traceability record](traceability.md), [Iteration 4 evidence](../iterations/iteration-4-release-1/README.md) and [existing release process](../releases/README.md). The [detailed plan](../release-1-plan.md) and existing issue assignments remain in place. No release completion, successful demonstration or stakeholder approval is asserted here.
