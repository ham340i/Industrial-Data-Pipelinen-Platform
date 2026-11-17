# Risks

## The risk most likely to kill the project

**We build a pipeline tool that does not fit the partner's real data and workflow.** The partner's source systems, data contracts and acceptance authority are not yet confirmed in writing, and no partner data has been used. A tool proven only on synthetic fixtures can pass every test and still be unusable.

How we attacked it first:

- Proved the whole data path without any UI in Iteration 1, so the engine never depends on the workbench: [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [experiment](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/experiments/headless_etl/README.md).
- Spiked safe read-only SQL connectivity before building the SQL source: [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), then [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23).
- Kept definitions portable and free of credentials and machine paths, so a pipeline authored on synthetic data can be pointed at approved sources later: [pipeline model](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/models.py).
- Remaining action: obtain a representative sanitized schema and a named acceptance contact from the partner. This is not done.

## Release 1 risk register

| Risk | Likelihood / impact | Mitigation and evidence | Owner | Status at Release 1 |
|---|---|---|---|---|
| Scope breadth: many block types plus UI, engine and governance | High / High | Vertical slice first ([#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10)), versioned block SDK ([#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8)) so blocks are added without engine changes | ham340i | Mitigated for Release 1: 32 of 34 items closed; packaging [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) open |
| Partner data and access not established | Unknown / High | Synthetic fixtures only; read-only SQL with bound parameters ([#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23)); security hardening [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | adamoug, GeorgesOgeil | Partly mitigated: boundaries hardened in [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32); still no partner data contract |
| Local hardware and memory limits | Unknown / High | Measured Polars and Arrow behaviour ([#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13)); fixed budgets on preview, execution and queries ([Performance](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Performance)) | karimikhaeil | Partly mitigated: synthetic representative workloads measured in [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35); not on partner hardware |
| UI complexity: graph, forms, diagnostics and persistence must share one contract | Medium / High | Configuration forms generated from block schemas ([#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17)); one validation rule set for API and executor ([#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21)); actionable errors ([#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33)) | aboudka2003, Al-Yousef | Mitigated; end-to-end Playwright workflow delivered in [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) |
| Schedule pressure and late integration | High / High | CI gates from Iteration 1 ([#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11)); cross-feature integration matrix ([#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37)) | menaboulus | Occurred: several items closed after their iteration date; see [release notes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Iteration-and-Release-Notes) |
| Incorrect ETL output (nulls, joins, precision) | Medium / High | Golden fixtures; explicit cast, overflow and null rules; data-quality blocks ([#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25)) | Al-Yousef | Mitigated by tests; no comparison against partner reference data yet |
| Credential or data exposure | Low / High | No credentials in definitions, log redaction, workspace containment ([Security](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Security)) | menaboulus | Mitigated in code and probed adversarially in [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) |
| Stakeholder unavailable for acceptance | Unknown / High | None effective yet | Team | Open: no signoff recorded for any iteration |

Risks are reviewed at each iteration boundary. A risk is closed only with linked evidence.
