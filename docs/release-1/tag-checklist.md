# Release 1 tag checklist

**Do not create the `Release1` tag until every item below is checked and linked.** Completing this list is the acceptance gate. Packaging the candidate ([#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36)) does not by itself approve the release.

Record the revision being tagged here: `5d05187c82ed62e30d2283c8a57e56990abd8ad1` (main after #106, checked November 17, 2026).

## Status on November 17, 2026

Engineering gates are met. Still open: the documentation gates (release notes and guides, in [#110](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/110)), the acceptance checklist's stakeholder demonstration, and the team agreement requested on [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38). Do not tag until those are done.

## Engineering gates

- [x] Every Release 1 issue is closed through a reviewed, merged pull request: #4, #31, #32, #34, #35, #36, #37. Approved and merged: #47, #89, #88, #93, #90, #106, #85.
- [x] All required CI checks pass on that exact revision, including "Release candidate rehearsal". [CI run 44171669873](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873).
- [x] The rehearsal report shows `"outcome": "passed"` for that revision. The CI job succeeded, and the same `smoke --report` run on the clean-install machine reported `passed` for `5d05187` ([report](../testing/release-1-clean-install-rehearsal.json)).
- [x] A clean install on a second machine follows [candidate.md](candidate.md) word for word: `start`, then `demo`, then `backup`, `reset --yes` and `restore --yes`. Ubuntu 24.04.5, Docker 29.9.2, all steps passed; one local-only certificate change for the machine's proxy is recorded ([install record](../testing/release-1-clean-install.md)).
- [x] No open pull request targets main with release-blocking changes. Open on November 17: #107 (Python dependency group), #110 (documentation), #111 (spike experiment).

## Documentation gates

- [ ] [Release notes](release-notes.md) list every merged feature and every known limitation still true at this revision.
- [ ] The README, architecture, Block SDK and operator guides match the tagged behavior.
- [x] Test results are recorded with revisions in [docs/testing](../testing/testing-plan.md), including the [clean install](../testing/release-1-clean-install.md).
- [x] The demonstration recording is made as described in [candidate.md](candidate.md#recording-the-demonstration) and linked here with its revision: [release-1-candidate-demo.webm](../demos/release-1-candidate-demo.webm), revision `5d05187`, November 17, 2026.

## Acceptance gates

- [ ] The [Release 1 acceptance checklist](acceptance.md) is complete for the tagged revision.
- [x] Stakeholder review status is recorded on [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38): not yet reviewed by the partner. The professor reviews academically and is not the stakeholder signoff authority.
- [ ] The team agrees in a recorded meeting or issue comment that the gates above are met.

## Creating the tag

Only after every box is checked, from an up-to-date main:

```bash
git tag -a Release1 <commit-sha> -m "Release 1: local vertical slice (see docs/release-1/release-notes.md)"
git push origin Release1
```

Then publish a GitHub release from the tag, using the release notes as its body.
