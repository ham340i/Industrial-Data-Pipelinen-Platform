# Infrastructure and tools

| Tool / environment | Current use | Decision still needed |
|---|---|---|
| Git / GitHub repository | Version control; origin points to ham340i/Industrial-Data-Pipelinen-Platform | Team access and protection verification |
| GitHub Issues / Projects | Templates supplied; live Project unconfigured by this work | Board owner, URL, fields/views and professor access |
| GitHub Actions | Repository checking workflows authored | First remote run and required-check setup |
| Python 3.11+ / Bash | Standard-library repository utilities | Not a product stack selection |
| GitHub CLI | Setup scripts require it; unavailable in audited environment | Install/authenticate on an authorized administrator’s machine |
| Product UI / engine / persistence | None | Evaluate against local-first constraints; record ADRs |
| Stakeholder hardware/data | Not inspected | Approved machine, workload envelope and data access |

No application package manager or dependencies exist. Add lockfile, reproducible install, caching and dependency checks with the selected ecosystem. Do not commit tool tokens or private workstation configuration.
