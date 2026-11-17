# Industrial Data Pipeline Engineering Platform

A SOEN 490 capstone project at Concordia University. Industry partner: **Pratt & Whitney Canada**. Product alias in the code and UI: **Local Pipeline Studio**.

The platform is a local-first visual ETL workbench. A process specialist draws a pipeline as a graph of blocks, checks it, previews intermediate data, runs it on their own workstation and publishes governed Parquet outputs that analytics and machine-learning work can query.

## Status at Release 1 (November 17, 2026)

- 33 of the 34 planned Release 1 work items are closed (224 of 232 story points). The open items are listed in the [release notes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Iteration-and-Release-Notes).
- Implemented and tested: visual builder, block library, schema-driven configuration, graph validation, bounded preview, local DAG execution, manual and timer triggers, run telemetry and monitoring, governed Parquet artifacts with bounded queries, a read-only SQL source, hardened file and SQL boundaries, and an end-to-end author, preview, execute and inspect workflow.
- 1,109 backend tests pass with 96% line coverage, and 226 frontend tests plus Playwright workflow tests run in CI.
- No stakeholder signoff, software license or demo video is recorded yet. Those are tracked in [remaining actions](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/SOEN490_HUMAN_ACTIONS.md).

## Contents

| Topic | Page |
|---|---|
| Set-up for a new developer | [Getting started](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Getting-Started) |
| Meeting records | [Meeting minutes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Meeting-Minutes) |
| What could stop the project | [Risks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Risks) |
| Terms for users | [User consent and end-user license agreement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/User-Consent-and-EULA) |
| Licence, IP, ethics, jobs | [Legal and ethical issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Legal-and-Ethical-Issues) |
| Value of the project | [Economic](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Economic) |
| Costs | [Budget](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Budget) |
| Who we build for | [Personas](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Personas) |
| Equity and accessibility | [Diversity statement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Diversity-Statement) |
| Layers, components, domain model | [Overall architecture and class diagrams](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Architecture) |
| Screens and user flows | [UI mockups (Figma prototype)](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/UI-Mockups) |
| Every library and tool, and why | [Infrastructure and tools](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Infrastructure-and-Tools) |
| Naming rules | [Name conventions](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Naming-Conventions) |
| Tests, CI and review | [Testing plan and continuous integration](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Testing-Plan-and-Continuous-Integration) |
| Threats and controls | [Security](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Security) |
| Limits and measurements | [Performance](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Performance) |
| Where it runs and how it is released | [Deployment plan and infrastructure](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Deployment-Plan-and-Infrastructure) |
| What we had to learn | [Missing knowledge and independent learning](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Missing-Knowledge-and-Independent-Learning) |
| Framework practices, logging, error handling | [Code quality practices](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Code-Quality) |
| Summary, velocity, retrospective, individuals | [Iteration and release notes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Iteration-and-Release-Notes) |

## Project links

- [Source repository](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform), [issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues), [pull requests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pulls), [milestones](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestones), [CI runs](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions)
- Project board: not linked yet. The repository owner must create it and share it with **moar82**; see [board setup](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/GITHUB_PROJECT_SETUP.md).
- [AI usage record](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/AI_USAGE.md)

This Wiki is published from `docs/wiki/` in the main repository; edit the source there.
