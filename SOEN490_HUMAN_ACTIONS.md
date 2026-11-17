# Remaining actions for Release 1

Updated November 17, 2026. These items need a person: a decision, a real event, or a statement only its author can truthfully make. Nothing here can be completed by tooling.

## Blocking a grade category

1. **AI declarations in source files.** 163 of 201 applicable source files (81%) now declare their AI contribution; the rubric needs 90%. The 104 headers added at Release 1 use only the level each file's own pull requests disclosed (the method is in [AI_USAGE.md](.github/AI_USAGE.md#source-file-declarations-added-at-release-1)). The 38 that remain were written in pull requests whose authors did not state how much AI generated, so only those authors can declare them:
   - **adamoug:** files from [#44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44) (FastAPI shell), [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52) (SQL spike) and [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72) (join, aggregate and sort tests)
   - **Al-Yousef:** files from [#48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48) (metadata) and [#51](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/51) (API integration fix)
   - **menaboulus:** files from [#65](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/65) (graph validation)

   Run `python3 scripts/check_ai_declarations.py` for the exact list. Add as the first line one of `# AI contribution: no substantial AI-generated code`, `# AI contribution: below 50% AI-generated` or `# AI contribution: 50% or more AI-generated` (`//` in TypeScript). If a declaration added at Release 1 is wrong for your file, correct it.
2. **AI declarations in pull requests.** Most merged feature and fix pull requests do not state one of the three levels. Each author edits their pull request description to add `AI contribution: <level>` and the list of AI-assisted files. The [template](.github/PULL_REQUEST_TEMPLATE.md) now asks for this.
3. **Life-Long Learning issues.** Only Al-Yousef ([#80](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/80)) and menaboulus ([#87](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/87)) have one. Every other student opens their own issue on the `Iteration 4 (Release 1)` milestone titled `[LLL] [Architecture: <subsystem>] Spike - <technical unknown>` with the four required sections (architectural context, knowledge gap, targeted learning plan, definition of done). A missing `[LLL]` prefix scores zero.
4. **Tag and publish the release.** After the open pull requests are settled and `main` is green: create tag `v1.0.0-release1` on the reviewed commit, create the GitHub Release from the [release notes](docs/releases/iteration-4-release-1.md), and record the tag, environment, date and outcome in the deployment record on the Wiki.
5. **Publish the Wiki.** After this branch merges, run `python3 scripts/publish_wiki.py --apply` from a machine with SSH access to GitHub, then open the Wiki and check the pages.

## Decisions and real-world evidence

6. **License.** Choose a license (the course recommends MIT) and commit `LICENSE`. Until then nobody has rights to the code.
7. **Meeting minutes.** None are recorded. Add the real ones to `docs/wiki/Meeting-Minutes.md` using the template there.
8. **Stakeholder signoff.** No review by the partner is recorded for any iteration. Demonstrate Release 1, record the feedback with the [signoff template](docs/stakeholder/signoff-template.md), and apply the `stakeholder:approved` or `stakeholder:changes-requested` label to the reviewed stories.
9. **Project board.** Create the GitHub Project, share it with **moar82**, and put its URL in the README.
10. **Demo video.** Record the Release 1 demo and link it in the README.
11. **Contractor rate.** Agree the hourly rate and its source so the contractor estimate in the release notes has a dollar figure.
12. **Budget.** Confirm the SonarCloud account and plan.

## Engineering still open

13. Review and merge or defer [#88](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/88) (security hardening, [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32)) and [#89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89) (Playwright workflow, [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31)), and finish [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) and [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36).
14. **Required checks.** Branch protection requires only the repository and documentation checks. Add `Backend checks`, `Frontend checks` and `Compose workspace smoke` as required.
15. **Merge method.** Disable squash and rebase merging in the repository settings so only merge commits are possible.
16. **Reviews.** From now on every approval must say what was examined. An approval without a technical comment does not count.
17. **Personal contribution records.** Missing for adamoug, GeorgesOgeil and PenguKev, and for several people's Iteration 4. A student with no record and no commits receives zero for the release.
18. **Closed stories.** Tick the acceptance criteria that were met and replace the "Pending" evidence text in each closed issue with links to its pull request and tests.
19. **Frontend size and complexity.** See the [documented exception](docs/refactoring/exceptions/frontend-components.md) and its plan.
20. **Roster.** The Release 1 plan checker lists eight students, while GeorgesOgeil and PenguKev also contribute. Update `docs/planning/release-1-backlog.json` and the checker if the team has ten members.
21. Answer or close [#58](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/58) (collaborator invitation).
