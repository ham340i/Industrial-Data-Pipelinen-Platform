# Release 1 tag checklist

**Do not create the `Release1` tag until every item below is checked and linked.** Completing this list is the acceptance gate. Packaging the candidate ([#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36)) does not by itself approve the release.

Record the revision being tagged here: `TODO: full commit SHA on main`.

## Engineering gates

- [ ] Every Release 1 issue is closed through a reviewed, merged pull request: #4, #31, #32, #34, #35, #36, #37.
- [ ] All required CI checks pass on that exact revision, including "Release candidate rehearsal". Link the run.
- [ ] The rehearsal report (`release-candidate-rehearsal` artifact) shows `"outcome": "passed"` for that revision.
- [ ] A clean install on a second machine follows [candidate.md](candidate.md) word for word: `start`, then `demo`, then `backup`, `reset --yes` and `restore --yes`. Record the operating system, Docker version and the observed result.
- [ ] No open pull request targets main with release-blocking changes.

## Documentation gates

- [ ] [Release notes](release-notes.md) list every merged feature and every known limitation still true at this revision.
- [ ] The README, architecture, Block SDK and operator guides match the tagged behavior.
- [ ] Test results are recorded with revisions in [docs/testing](../testing/testing-plan.md).
- [ ] The demonstration recording is made as described in [candidate.md](candidate.md#recording-the-demonstration) and linked here with its revision.

## Acceptance gates

- [ ] The [Release 1 acceptance checklist](acceptance.md) is complete for the tagged revision.
- [ ] Stakeholder review status is recorded on [#38](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/38). The professor reviews academically and is not the stakeholder signoff authority.
- [ ] The team agrees in a recorded meeting or issue comment that the gates above are met.

## Creating the tag

Only after every box is checked, from an up-to-date main:

```bash
git tag -a Release1 <commit-sha> -m "Release 1: local vertical slice (see docs/release-1/release-notes.md)"
git push origin Release1
```

Then publish a GitHub release from the tag, using the release notes as its body.
