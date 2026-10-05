# SOEN 490 human actions

Updated October 4, 2026 (America/Toronto). Labels and all 13 milestones exist, and GitHub reports main as protected. The [current team audit](docs/team-readiness-2026-10-04.md) records live delivery evidence and the limits of available administration access. The [earlier compliance audit](docs/SOEN490_COMPLIANCE_AUDIT.md) remains a historical snapshot.

## Next actions

1. **Complete independent review of [metadata PR #48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48) and the integration correction tracked by [#49](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/49).** PR #48 has passing CI and `joedaswagger` requested. PR #3 is already merged after approval; it is no longer an open action. An administrator must verify the actual required backend/frontend/Compose gates and independent approval settings; current WRITE access cannot inspect classic protection configuration.
2. **Create/reuse the GitHub Project.** Follow [exact setup](docs/GITHUB_PROJECT_SETUP.md); current credentials lack Projects scope. Configure the documented fields/views, link real issues, paste the Project URL into README and share it with **moar82**. Verify the professor can see items and demos.
3. **Maintain the published Wiki.** The [Wiki](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki) was published at commit `6984b4d`. Update sources in `docs/wiki/` and use the [publisher](scripts/github-setup/wiki-setup.md) for future changes. Its documentation links currently use planning revision `0caf6f9`; refresh them after the documentation merges into `main`.
4. **Deliver the already assigned Iteration 1 work, then refine the next two iterations.** The [current owner checklist](docs/team-readiness-2026-10-04.md#iteration-1-work-that-must-become-reviewable) identifies #8/#9/#10/#12/#13 with no published implementation PR. The original Release 1 stories, assignments and estimates exist; refine availability, interfaces and scope without creating duplicate stories or inventing past hours. Prepare the [Iteration 1 demo](docs/iterations/iteration-1/demo.md).
5. **Confirm stakeholder and technical constraints.** Provide acceptance authority, review cadence, approved source/output contracts, access permission, representative sanitized data and local hardware limits. Refine the supplied [Release 1 target](docs/architecture/release-1-target.md), record detailed ADRs, then implement and test the first slice.

## Decisions and evidence the team must supply

- [ ] Confirm supplied course dates and the actual submission time/time zone; prepare the presentation, peer evaluations and stakeholder feedback due by April 13, 2027.
- [ ] Approve IP ownership, stakeholder/data agreements, NDA applicability and software license. MIT remains only a candidate; no LICENSE is selected. Keep confidential signed documents in restricted storage.
- [ ] Decide whether [consent/EULA](docs/user-consent-eula.md) is needed and obtain appropriate review; the draft is not approved or effective.
- [ ] Validate personas/accessibility needs, assign risk owners and review mitigation evidence early each iteration.
- [ ] Confirm budget, plan allowances, expenses/credits and authorized receipts; review the observed SonarCloud integration and its permissions/data handling.
- [ ] Confirm intended public Git identity; older commit metadata contains a non-noreply email. Use GitHub noreply prospectively if appropriate; do not rewrite history without a separate coordinated decision.
- [ ] Approve a dedicated private security/support contact and verify the repository's private-reporting route.
- [ ] Establish application dependency maintenance: Dependabot PR #1 already merged, but the configuration covers GitHub Actions only. Plan reviewed frontend npm updates and deliberate regeneration/verification of the Python hash lock.
- [ ] Each contributor records actual [personal engineering contributions](docs/individual-contributions/README.md), tests, learning, failed experiments and AI assistance every iteration/release. Do not claim AI-generated scaffolding as personally authored product engineering.
- [ ] Record actual meetings, decisions, code reviews, application tests and performance measurements; add approved stakeholder feedback and signoffs.
- [ ] Complete real iteration/release notes, velocity and justified contractor estimates. Create tags only on reviewed completed states and provide actual demo URLs with verified access.

The largest remaining delivery/evidence gaps are a shared live Project, a working/tested ETL slice, per-student engineering evidence, authorized stakeholder feedback, and completed iteration/release/demo records. Templates do not close these gaps. Full Release 1 acceptance tracker #38 is open again; documentation merges must not close it.

## Release 1 planning follow-up

Use the [assigned Release 1 report](docs/release-1-setup-report.md) and [workload](docs/release-1-workload.md) to confirm estimates, availability and reviewer rotation. The eight students are explicitly listed there; **moar82 is the professor, never an engineering assignee or routine reviewer**. Current professor invitation/access status has not been reverified in this audit; verify it with the owner. Project sharing requires authorized access because current API credentials lack Projects scope. The product backlog supersedes the earlier absence of planned stories; the [current audit](docs/team-readiness-2026-10-04.md) distinguishes completed foundations from outstanding product work.
