# SOEN 490 human actions

Labels, all 13 milestones and main protection are now configured. The [current audit](docs/SOEN490_COMPLIANCE_AUDIT.md) records what was verified. Only actions requiring human decisions, access or real evidence remain below.

## Next actions

1. **Review [compliance PR #3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3), linked to [issue #2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/2).** One independent teammate must approve after CI passes; main is protected, including administrators. No self-approval or fabricated review is allowed.
2. **Create/reuse the GitHub Project.** Follow [exact setup](docs/GITHUB_PROJECT_SETUP.md); current credentials lack Projects scope. Configure the documented fields/views, link real issues, paste the Project URL into README and share it with **moar82**. Verify the professor can see items and demos.
3. **Maintain the published Wiki.** The [Wiki](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki) was published at commit `6984b4d`. Update sources in `docs/wiki/` and use the [publisher](scripts/github-setup/wiki-setup.md) for future changes. Its documentation links currently use planning revision `0caf6f9`; refresh them after the documentation merges into `main`.
4. **Plan the next two iterations.** Approve a small product vertical slice, assign every student substantial engineering work, create real stories, estimate points/ideal hours, and attach the correct [milestones](docs/milestones.md). Do not retroactively invent estimates for completed setup.
5. **Confirm stakeholder and technical constraints.** Provide acceptance authority, review cadence, approved source/output contracts, access permission, representative sanitized data and local hardware limits. Refine the supplied [Release 1 target](docs/architecture/release-1-target.md), record detailed ADRs, then implement and test the first slice.

## Decisions and evidence the team must supply

- [ ] Confirm supplied course dates and the actual submission time/time zone; prepare the presentation, peer evaluations and stakeholder feedback due by April 13, 2027.
- [ ] Approve IP ownership, stakeholder/data agreements, NDA applicability and software license. MIT remains only a candidate; no LICENSE is selected. Keep confidential signed documents in restricted storage.
- [ ] Decide whether [consent/EULA](docs/user-consent-eula.md) is needed and obtain appropriate review; the draft is not approved or effective.
- [ ] Validate personas/accessibility needs, assign risk owners and review mitigation evidence early each iteration.
- [ ] Confirm budget, plan allowances, expenses/credits and authorized receipts; review the observed SonarCloud integration and its permissions/data handling.
- [ ] Confirm intended public Git identity; older commit metadata contains a non-noreply email. Use GitHub noreply prospectively if appropriate; do not rewrite history without a separate coordinated decision.
- [ ] Approve a dedicated private security/support contact and verify the repository's private-reporting route.
- [ ] Review existing Dependabot PR #1; no dependency upgrade was merged by this follow-up.
- [ ] Each contributor records actual [personal engineering contributions](docs/individual-contributions/README.md), tests, learning, failed experiments and AI assistance every iteration/release. Do not claim AI-generated scaffolding as personally authored product engineering.
- [ ] Record actual meetings, decisions, code reviews, application tests and performance measurements; add approved stakeholder feedback and signoffs.
- [ ] Complete real iteration/release notes, velocity and justified contractor estimates. Create tags only on reviewed completed states and provide actual demo URLs with verified access.

The largest remaining grading gaps are a shared live Project, a working/tested product, per-student engineering evidence, authorized stakeholder feedback, and completed iteration/release/demo records. Templates do not close these gaps.

## Release 1 planning follow-up

Use the [assigned Release 1 report](docs/release-1-setup-report.md) and [workload](docs/release-1-workload.md) to confirm estimates, availability and reviewer rotation. The eight students are explicitly listed there; **moar82 is the professor, never an engineering assignee or routine reviewer**. His repository invitation is pending and has been preserved. Project sharing still requires an authorized owner because current API credentials lack Projects scope. The new product backlog supersedes the earlier absence of planned stories; actual implementation and evidence remain pending.
