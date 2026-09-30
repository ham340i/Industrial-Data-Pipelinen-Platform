# Release 1 engineering plan

Project: **Industrial Data Pipeline Engineering Platform** (existing repository/product alias: Local Pipeline Studio).
Industry partner: **Pratt & Whitney Canada**, as supplied by the team. No data access, signed agreement, stakeholder representative or approval is inferred.

## Baseline audit

Main is `609b617`; open compliance PR #3 is based on `docs/2-soen490-compliance` at `c891df2`. The Release 1 planning branch builds on that PR without replacing it; [planning PR #39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39) is stacked on it. Merge #3 first, then retarget #39 to main and verify review/check gates. Existing code consists of Python/Bash repository utilities and 12 tool tests, not an application. React/FastAPI/Polars and product test frameworks are not installed. The existing CI checks repository tooling/docs. The only pre-existing issues/PRs are technical issue #2, compliance PR #3 and Dependabot PR #1; none duplicates this product backlog. All 13 milestones and management labels already exist; reuse them.

Only ham340i-attributed repository setup history is available; it does not establish anyone’s frontend/backend expertise. All eight named students have assignment access. GitHub spells the supplied MarcelHaddad1 account `MarcElHaddad1` (same case-insensitive identity). Other collaborators retain access but are excluded from this Release 1 workload. The professor’s repository invitation is pending and is not modified. Projects API access remains blocked by missing Projects scope.

## Scope and estimates

Plan 34 future work items: one substantial owner assignment per student per iteration, plus two focused Iteration 1 risk spikes. Estimates are initial Fibonacci planning points and ideal engineering hours, including implementation, feature tests and documentation. They are not historical work, promises or measured productivity. Reviewer effort is estimated separately; point totals are not duplicated for reviewers. Confirm availability and refine before starting. Revisit Iterations 3–4 after each demo while retaining the supplied Release 1 acceptance goal; the detailed commitment window is the next two iterations.

Each primary designs, implements, tests and records evidence. Reviewer rotation and cross-layer assignments avoid permanent silos. Interface drafts and mocks allow parallel starts; dependency links mean prerequisites for completion/integration, not that all design work must wait.

## Acceptance scenario

Launch locally → create/open project → browse/drag/connect/configure blocks → validate graph/config → preview supported intermediate data → execute CSV → Validate Schema → Filter → Join(SQL) → Aggregate → Parquet → inspect status, block timings, row counts, logs and failures → query output → save/reload and rerun without source edits.

All acceptance checks remain unchecked until demonstrated and tested. Manual and a bounded in-process Timer trigger are included; advanced scheduling is excluded. Schema Validation and Validate Schema refer to one reusable block. REST ingestion is optional and uncommitted. Kafka, MQTT, OPC UA, distributed execution, enterprise identity, a complete ontology and all transform categories are out of scope.

## Target architecture and work breakdown

See [target architecture](architecture/release-1-target.md), [Block SDK contract plan](architecture/block-sdk-release-1.md), [backlog](planning/release-1-backlog.json), [workload](release-1-workload.md), [dependencies](release-1-dependencies.md), [review plan](code-review-plan.md), [traceability](release-1-traceability.md), and the [setup report](release-1-setup-report.md).

No Release 1 application is implemented by this planning change. No student contribution, approval, benchmark or release tag is fabricated.

## Release 1 risk register

Likelihood/impact below are planning assessments, not measured failures or claims about partner access. Primary owners investigate; shared scope/acceptance decisions still require the team and authorized partner.

| Risk | Likelihood / impact | Why it matters | Early mitigation work | Owner | Status |
|---|---|---|---|---|---|
| Scope breadth | High / High | 19 block types plus UI, engine and governance in four iterations | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) | ham340i | Open; mitigation planned |
| Data/security access | Unknown / High | Partner data or permissions are not established by the brief | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | adamoug | Open; mitigation planned |
| Performance uncertainty | Unknown / High | Local hardware/type/memory limits could invalidate design assumptions | [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) | karimikhaeil | Open; mitigation planned |
| UI complexity | Medium / High | Graph, forms, diagnostics and persistence must share one contract | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17), [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) | aboudka2003 | Open; mitigation planned |
| Schedule pressure | High / High | Short I1 and late integration dependencies reduce recovery time | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11), [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) | menaboulus | Open; mitigation planned |
| Industrial connectivity | Unknown / High | Supported SQL dialect and source model must be proven without assumed access | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) | adamoug | Open; mitigation planned |
