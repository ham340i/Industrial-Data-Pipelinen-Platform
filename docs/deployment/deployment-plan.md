# Deployment plan

No product is runnable or packaged yet. Only repository checks run locally and in GitHub Actions. See [planned deployment diagram](../architecture/deployment-architecture.md).

| Environment | Intended use | Requirements before use |
|---|---|---|
| Development | Implement and run synthetic pipelines locally | Implement the supplied Release 1 stack and document exact setup/start/test commands |
| Test | Repeatable automated validation | Isolated fixtures/storage, locked dependencies, reproducible test runner |
| Stakeholder/local | Demonstrate on approved workstation and sources | Data approval, credential setup, hardware validation, acceptance script |
| Future production | Supported local installation | Packaging/signing decision, upgrade/rollback, recovery, support and security review |

## Planned release progression

Stakeholder release → trusted testers → alpha → beta → broader deployment. None of these stages has occurred. Advance only with recorded test results, known limitations and authorized feedback.

Before shipping, document artifact origin/checksum, prerequisites, configuration, install/start/stop, local storage and network behavior. Test upgrade and backup/restore using synthetic data. Associate every artifact with the reviewed release tag and locked dependencies. Define rollback compatibility before schema migration; preserve user data and credentials. The release owner and support channel remain to be assigned.

## Course rollout stages applied to this project

1. **Stakeholder:** approved workstation and authorized datasets, with recorded acceptance feedback.
2. **Family/friends / trusted testers:** optional usability checks using synthetic data only; never share restricted manufacturing sources or credentials.
3. **Alpha:** narrow documented connector/block scope and known limitations.
4. **Beta:** broader approved workloads, regression/performance evidence and tested upgrade/recovery.
5. **Full release plan:** agreed support, packaging, security, compatibility and acceptance criteria.

All stages are planned. A public SaaS deployment is not assumed for a local-first tool.

## Monitoring and deployment record

For an implemented product, define local run health/error reporting, redacted logs, retention and opt-in diagnostics before release. No monitoring service is currently deployed.

Copy this record for each actual deployment:

- Environment / approved machine class: TODO
- Date / operator GitHub identity: TODO
- Release tag, commit and artifact checksum: TODO
- Configuration reference (no secrets): TODO
- Data approval and backup: TODO
- Install/upgrade commands actually run: TODO
- Smoke tests / health/log evidence: TODO
- Result / failures / rollback performed: TODO
- Rollback target and data-compatibility constraints: TODO
- Related issue, PR and stakeholder review: TODO

## Frontend foundation artifact

Issue #5 adds `frontend/dist/` via `npm ci` and `npm run build` in `frontend/`. `npm run preview` serves a loopback verification build. Hash routing works on static hosting without route rewrites. `VITE_API_BASE_URL` is embedded at build time and must reference the intended API with matching CORS configuration. This is not a complete ETL deployment; the backend, storage and execution services remain future work. See the [frontend guide](../frontend/workbench.md).
