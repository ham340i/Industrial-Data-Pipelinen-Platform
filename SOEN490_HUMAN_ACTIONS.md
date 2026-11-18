# Remaining actions for Release 1

Updated November 17, 2026. These items need a person: a decision, a real event, or a statement only its author can truthfully make. Nothing here can be completed by tooling.

## Blocking a grade category

1. **AI declarations in source files.** 179 of 214 applicable source files (83%) declare their AI contribution; the rubric needs 90%. Declarations added at Release 1 use only the level each file's own pull requests disclosed (method in [AI_USAGE.md](.github/AI_USAGE.md#source-file-declarations-added-at-release-1)). The 35 that remain were written in pull requests whose authors did not state how much AI generated, so only those authors can declare them:
   - **adamoug:** files from [#44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44) (FastAPI shell), [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52) (SQL spike) and [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72) (join, aggregate and sort tests)
   - **Al-Yousef:** files from [#48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48) (metadata) and [#51](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/51) (API integration fix)
   - **joedaswagger:** `tests/test_execution_failures.py` from [#93](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/93)
   - **menaboulus:** files from [#65](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/65) (graph validation)

   Run `python3 scripts/check_ai_declarations.py` for the exact list. Add as the first line one of `# AI contribution: no substantial AI-generated code`, `# AI contribution: below 50% AI-generated` or `# AI contribution: 50% or more AI-generated` (`//` in TypeScript). If a declaration added at Release 1 is wrong for your file, correct it.
2. **AI declarations in pull requests.** Most merged feature and fix pull requests do not state one of the three levels. Each author edits their pull request description to add `AI contribution: <level>` and the list of AI-assisted files. The [template](.github/PULL_REQUEST_TEMPLATE.md) now asks for this.
3. **Life-Long Learning issues.** Al-Yousef ([#80](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/80)), menaboulus ([#87](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/87)) and ham340i ([#109](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/109)) are complete. adamoug ([#92](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/92)) must add `Spike - <technical unknown>` to the title; karimikhaeil ([#91](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/91)) must rename it to the required format and set the `Iteration 4 (Release 1)` milestone. aboudka2003, joedaswagger, MarcElHaddad1, GeorgesOgeil and PenguKev have not opened one. The required title is `[LLL] [Architecture: <subsystem>] Spike - <technical unknown>`, on the Release 1 milestone, with the four sections (architectural context, knowledge gap, targeted learning plan, definition of done). A missing `[LLL]` prefix scores zero.
4. **Tag and publish the release.** After the open pull requests are settled and `main` is green: create tag `Release1` on the reviewed commit, create the GitHub Release from the [release notes](docs/releases/iteration-4-release-1.md), and record the tag, environment, date and outcome in the deployment record on the Wiki.
5. **Publish the Wiki.** After this branch merges, run `python3 scripts/publish_wiki.py --apply` from a machine with SSH access to GitHub, then open the Wiki and check the pages.

## Decisions and real-world evidence

6. **License.** Choose a license (the course recommends MIT) and commit `LICENSE`. Until then nobody has rights to the code.
7. **Meeting minutes.** No minutes were taken during Release 1; the [team activity log](docs/meetings/team-activity-log-release-1.md) reconstructs the GitHub work around each Monday and Wednesday. From Iteration 5, record each meeting in `docs/wiki/Meeting-Minutes.md` using the template there.
8. **Stakeholder signoff.** Release 1 was accepted by the stakeholder (Taconics, represented by ham340i): see the [Release 1 signoff](docs/stakeholder/release-1-signoff.md). Apply the `stakeholder:approved` label to the reviewed stories.
9. **Project board.** Create the GitHub Project, share it with **moar82**, and put its URL in the README.
10. **Demo video.** The Release 1 presentation is linked in the README. Make sure the OneDrive link is shared so the instructor can open it, and that the recording includes the live product demo and code walkthrough.
11. **Contractor rate.** Agree the hourly rate and its source so the contractor estimate in the release notes has a dollar figure.
12. **Budget.** Confirm the SonarCloud account and plan.

## Engineering still open

13. Release 1 engineering is complete (#105 and #106 merged). Before tagging `Release1`, complete the team's [tag checklist](docs/release-1/tag-checklist.md): clean install on a second machine, demo recording, acceptance checklist, stakeholder status on #38 and a recorded team agreement.
14. **Required checks.** Branch protection requires only the repository and documentation checks. In Settings → Branches → `main`, add `Backend checks`, `Frontend checks`, `Compose workspace smoke` and both `Standalone workspace smoke` jobs as required.
15. **Merge method.** In Settings → General → Pull Requests, untick "Allow squash merging" and "Allow rebase merging" so only merge commits are possible.
16. **Reviews.** From now on every approval must say what was examined. An approval without a technical comment does not count.
17. **Personal contribution records.** Missing entirely for adamoug, GeorgesOgeil and PenguKev, and for Iteration 4 from joedaswagger and MarcElHaddad1. A student with no record and no commits receives zero for the release.
18. **Closed stories.** Each closed story now has a comment linking its merged pull requests and test evidence. Owners still need to tick the acceptance criteria that were met; that is a claim only the owner and reviewer can make.
19. **Frontend size and complexity.** The API parsers are fixed; the React components remain. See the [documented exception](docs/refactoring/exceptions/frontend-components.md) and its plan.
20. **Roster.** The Release 1 plan checker lists eight students, while GeorgesOgeil and PenguKev also contribute. Update `docs/planning/release-1-backlog.json` and the checker if the team has ten members.
21. Answer or close [#58](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/58) (collaborator invitation).
