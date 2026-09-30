# Legal and ethical review checklist

Status: questions for authorized team/stakeholder review, not legal conclusions or signed agreements.

| Area | Decision/evidence needed |
|---|---|
| IP | Identify who owns student work, stakeholder contributions and third-party assets; record approval of reuse terms |
| Software license | Approve a compatible license and dependency/asset obligations before distribution |
| Stakeholder agreement | Confirm deliverables, access, review authority, support expectations and permitted publication |
| NDA | Determine applicability and approved storage; do not publish confidential documents |
| Privacy | Minimize personal information in sources, logs, screenshots, commits and public evidence |
| Data ownership | Confirm rights to ingest, transform, retain, share and delete each dataset and derived output |
| Security | Review credentials, workstation access, connector permissions and incident responsibilities |
| Ethical use | Avoid misleading data-quality claims; show limitations, provenance and failed validations |
| Environment | Measure resource consumption and avoid unnecessary repeated heavy processing |
| Accessibility, equity and diversity | Validate keyboard access, visual clarity, understandable errors and different technical experience levels |
| Employment and job disruption | Discuss effects on process specialists; preserve human oversight, provide training and avoid unsupported productivity/job claims |

Owner, review date and approved evidence references: TODO. Link outcomes to issues, risks and ADRs. Never represent a checklist as stakeholder consent.

## Third-party services and consent

GitHub stores repository, issue and CI metadata. A SonarCloud check was observed on the baseline revision with a neutral result; repository-local SonarCloud configuration and its account/data-retention choices were not found. The owner should verify the integration’s permissions and intended scope. Do not infer that product data is approved for either service.

Decide whether user consent or an EULA is applicable before introducing telemetry, external processing or distribution; use the clearly unapproved [draft](../user-consent-eula.md). No acceptance or legal review is claimed.
