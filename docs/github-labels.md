# GitHub labels

The supplied Release 1 brief now authorizes actual future work in named product areas. Feature labels categorize this planned scope; none implies an implemented feature. Existing labels were preserved.

| Category | Labels / policy |
|---|---|
| Product features | `feature:frontend`, `feature:builder`, `feature:block-sdk`, `feature:api`, `feature:execution-engine`, `feature:validation`, `feature:sources`, `feature:transforms`, `feature:data-quality`, `feature:preview`, `feature:parquet`, `feature:metadata`, `feature:telemetry`, `feature:testing`, `feature:documentation` |
| DevOps equivalent | Reuse `feature:infrastructure`; do not create duplicate `feature:devops` |
| Work types | `type:story`, `type:task`, `type:spike`, `type:bug`, `type:documentation`; reuse `type:task` instead of duplicate `type:technical` |
| Release | `release:1` for assigned work and the acceptance tracker |
| Priority | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` |
| Risk | `risk:high`, `risk:medium`, `risk:low` |
| Stakeholder | `stakeholder:review`, `stakeholder:approved`, `stakeholder:changes-requested`; apply only with the actual review state |

See the [catalog](../scripts/github-setup/labels.json) and [Release 1 backlog](planning/release-1-backlog.json). REST sources, advanced connectors and unrelated product categories remain uncommitted. Keep one primary feature per work item unless a real cross-feature query needs another label.
