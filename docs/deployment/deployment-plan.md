# Deployment plan

No product is runnable or packaged yet. Only repository checks run locally and in GitHub Actions. See [planned deployment diagram](../architecture/deployment-architecture.md).

| Environment | Intended use | Requirements before use |
|---|---|---|
| Development | Implement and run synthetic pipelines locally | Select stack, document exact setup/start/test commands |
| Test | Repeatable automated validation | Isolated fixtures/storage, locked dependencies, reproducible test runner |
| Stakeholder/local | Demonstrate on approved workstation and sources | Data approval, credential setup, hardware validation, acceptance script |
| Future production | Supported local installation | Packaging/signing decision, upgrade/rollback, recovery, support and security review |

## Planned release progression

Stakeholder release → trusted testers → alpha → beta → broader deployment. None of these stages has occurred. Advance only with recorded test results, known limitations and authorized feedback.

Before shipping, document artifact origin/checksum, prerequisites, configuration, install/start/stop, local storage and network behavior. Test upgrade and backup/restore using synthetic data. Associate every artifact with the reviewed release tag and locked dependencies. Define rollback compatibility before schema migration; preserve user data and credentials. The release owner and support channel remain to be assigned.
