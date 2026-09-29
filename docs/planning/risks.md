# Risk register

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
