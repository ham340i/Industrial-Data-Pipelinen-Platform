# GitHub labels

Live setup created the labels below while preserving existing generic and Dependabot labels. No product application is implemented, so only the implemented repository infrastructure has an active feature label. Labels categorize work; they do not prove feature completion.

| Active category | Labels | Use |
|---|---|---|
| Implemented feature | `feature:infrastructure` | Repository tools, CI and documentation infrastructure |
| Type | `type:story`, `type:bug`, `type:task`, `type:spike`, `type:documentation` | One primary work type |
| Risk | `risk:high`, `risk:medium`, `risk:low` | Assessed delivery/technical risk with rationale |
| Priority | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` | Agreed business/engineering priority |
| Stakeholder | `stakeholder:review`, `stakeholder:approved`, `stakeholder:changes-requested` | Actual review status, with evidence for approval |
| AI | `ai-assisted` | Meaningful assistance; detailed disclosure still required |

The [active catalog](../scripts/github-setup/labels.json) and [create-only helper](../scripts/github-setup/README.md) support safe reruns. Retain `type:task` rather than adding an equivalent `type:technical` alias.

## Proposed product labels — not created

These came from the project brief, not implemented code. Add a label only when the team accepts real feature scope and links it to a story/design; do not imply completed functionality.

- `feature:visual-builder` — Visual pipeline authoring and configuration.
- `feature:data-ingestion` — Approved file, SQL and REST ingestion.
- `feature:transformations` — Reusable transformation blocks.
- `feature:data-quality` — Schema validation and data-quality rules.
- `feature:execution-engine` — Local orchestration and reproducibility.
- `feature:data-preview` — Intermediate data inspection.
- `feature:versioning` — Pipeline revisions and reuse.
- `feature:run-history` — Run metadata, diagnostics and logging.
- `feature:governed-output` — Validated datasets and publication.
- `feature:local-api` — Potential local output API.
- `feature:analytics` — Analytics consumer integration.
- `feature:ml-preparation` — ML-ready data preparation.
- `feature:security` — Credentials, privacy and access boundaries.
