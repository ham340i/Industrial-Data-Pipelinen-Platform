# User consent and EULA — draft for review

**DRAFT — not legally reviewed, approved, accepted or in effect.** No application or user-consent mechanism exists. The team and stakeholder must first decide whether this local-first tool needs consent, contractual terms, an EULA, or a different agreement. Do not present this text as a valid consent flow or license grant.

## Applicability decision

Owner/reviewer: TODO authorized role
Decision date and related issue: TODO
Required agreement and consent mechanism: TODO, or documented not applicable with rationale

## Proposed terms to resolve

| Area | Draft content / decision requiring confirmation |
|---|---|
| Data collection | Identify actual imported data, local run metadata and optional diagnostics; no telemetry is implemented or assumed |
| Purpose | Process approved manufacturing inputs into validated outputs for agreed workflows |
| Storage | Specify local locations, retention, deletion, backups and who can access data; all undecided |
| Third-party processing | List actual external connectors/services before use; do not assume local-first means no network transfer |
| User responsibilities | Use only data/accounts the user is authorized to process; protect credentials and follow stakeholder policy |
| Limitations | Explain supported workloads, validation limits and known defects based on measured behavior; do not promise safety-critical suitability |
| Termination/withdrawal | Decide how users stop processing, revoke connector access and request/delete retained data; document constraints on existing exports |
| Liability | TODO qualified review of appropriate terms; no enforceability or warranty conclusion supplied |
| Contact | TODO team-approved support/privacy contact; do not insert personal contact information |

If consent is required, define clear language, affirmative action, accessible presentation, version/date, a record of the agreed scope and a way to decline. Never bundle unapproved data sharing into a default setting. Confirm how revised terms are communicated. Test the actual flow when implemented and keep approval evidence in authorized storage.

Related decisions: [license/IP](legal/README.md), [legal/ethical review](legal/legal-and-ethical-issues.md), [security](security/security-plan.md).
