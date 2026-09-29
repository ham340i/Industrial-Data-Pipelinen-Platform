# Risk register

The observed risks below are grounded in this repository/API audit. Earlier project hypotheses follow separately and remain unvalidated.

## Observed priorities before the next iteration

| Risk | Likelihood | Impact | Why it matters | Mitigation | Evidence / related issue | Owner | Status |
|---|---|---|---|---|---|---|---|
| E1: No runnable product or selected stack | Gap present | Could prevent demonstrable engineering delivery | Repository tooling alone cannot satisfy substantial product implementation | Agree and implement one tested vertical slice after a stack ADR | No application manifests/source; [audit](../SOEN490_COMPLIANCE_AUDIT.md), issue #2 | Team must assign | Open; setup does not resolve this |
| E2: Project access/setup blocked | Gap present | Course planning evidence inaccessible | Current API cannot inspect/create Projects | Owner configures browser board or grants project scope; share with moar82 | API INSUFFICIENT_SCOPES; [setup](../GITHUB_PROJECT_SETUP.md) | Repository owner | Open |
| E3: Missing per-student stories/evidence | Gap present in inspected repository | Individual course outcomes cannot be assessed | A technical setup issue is not every student’s engineering contribution | Plan two iterations, assign real work and maintain personal records | No product stories/iteration records; [personal records](../individual-contributions/README.md) | Team must assign | Open |
| E4: Unconfirmed source/output and acceptance contracts | No approved contract recorded; real availability unknown | Wrong design may require major rework | Proposed ETL scope has no recorded validated data contract | Obtain an approved representative schema/workflow and acceptance criteria early | [proposed architecture](../architecture/system-architecture.md), no signoff record | Team/stakeholder must assign | Open; do not infer stakeholder unavailability |
| E5: Public attribution/data-handling decisions unresolved | Metadata exposure present; future data risk unassessed | Privacy or agreement failures can restrict collaboration | Commit metadata includes a non-noreply email and legal/data decisions are pending | Confirm public identity, use noreply prospectively, approve data access before samples are added | [privacy review](../SOEN490_COMPLIANCE_AUDIT.md#privacy-review), [legal register](../legal/README.md) | Repository owner / team | Open; no history rewrite |

## Earlier project hypotheses — validate before treating as facts

Initial hypotheses for team validation. Probability and impact are **unassessed** until evidence is gathered; owners must be assigned during planning. Prioritize risks that could prevent a usable, accepted product.

| ID / Risk | Probability | Impact | Why it matters | Mitigation / next evidence | Evidence / related issues | Owner | Status |
|---|---|---|---|---|---|---|---|
| R1: Stakeholder data unavailable | TBD | Potential project blocker | Synthetic success may not transfer to real manufacturing workflows | Confirm permitted samples, schemas and access date; define sanitized fallback | TODO | Unassigned | Validate |
| R2: Existing data-model mismatch | TBD | Potential project blocker | Outputs may be unusable by existing consumers | Review a real source-to-output contract before connector implementation | TODO | Unassigned | Validate |
| R3: Scope exceeds team capacity | TBD | Potential project blocker | Builder, connectors, engine and governance can each consume a capstone | Agree one end-to-end vertical slice and defer optional connectors/API/ML features | TODO | Unassigned | Validate |
| R4: Local hardware limits | TBD | Potential project blocker | Large workloads may exhaust workstation memory | Obtain approved hardware/workload envelope; spike bounded execution and previews | TODO | Unassigned | Validate |
| R5: Incorrect ETL outputs | TBD | Potential project blocker | Silent null/join/precision errors undermine trust | Golden fixtures, explicit contracts and stakeholder comparison datasets | TODO | Unassigned | Validate |
| R6: Connector complexity/access | TBD | High candidate impact | SQL/REST auth and schema drift can derail schedule | Validate one approved connector first; test failure/retry behavior | TODO | Unassigned | Validate |
| R7: Credential/data exposure | TBD | High candidate impact | Leaks may revoke data access and harm stakeholder | Secret isolation, redaction, approved fixtures and review | TODO | Unassigned | Validate |
| R8: Stakeholder unavailable | TBD | Potential project blocker | Acceptance and scope decisions may stall | Agree review cadence, authorized delegate and escalation route | TODO | Unassigned | Validate |

Review each iteration: update probability/impact rationale, owner, mitigation issue and status (Open, Mitigating, Accepted with rationale, Closed with evidence). Escalate blockers immediately. Do not silently mark risks resolved.
