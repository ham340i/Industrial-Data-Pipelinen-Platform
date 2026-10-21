# Issue #17 acceptance and verification

Implementation is on `feature/17-configuration-panel`, based on
merged main `58bc06b` (includes #15/#14 canvas/persistence and #21 validation).
Verified implementation commit: `883dfc9`. Subsequent evidence-only commits add
this record, usage links and screenshots without changing executable code.
Checks were executed October 21, 2026 against this branch. Publishing, hosted CI
and independent review remain separate from the local implementation evidence.
Published in [PR #66](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/66);
review requested from @karimikhaeil on October 21. Independent review and merge
remain pending.

| Requirement from issue #17 | Implementation / meaningful check | State |
| --- | --- | --- |
| Typed controls from the bounded public SDK schema | `configuration/schema.ts`, `BlockConfigPanel.tsx`; SDK fixture and typed controls, unsupported rules rejected visibly | PASS |
| Per-node values survive selection and real serialization/save/load | existing graph `nodes[].data.config`, editor update action; component and real-API browser round trip with 42/7, failed copy retains 43 | PASS |
| Required/type/range errors identify field and block | local checks plus current backend diagnostics beside inputs; required, fractional integer, -1000 boundary and 1001 rejection; manual diagnostic click focused Amount | PASS |
| Accessible valid/loading/error/empty/version states | labelled controls, status/alert, retry, keyboard/focus checks; 390x844 real-browser selection/editing and visual inspection | PASS |
| References instead of runtime credentials/paths | known credential/runtime keys and absolute paths rejected; logical references accepted; unsafe defaults cannot create nodes and imported values are concealed without erasure | PASS |
| Current dependency integration and regression checks | #6/#8/#15 merged; actual registry, canvas, validation API and project persistence; final production browser and local regressions below | PASS locally |
| Documentation | feature guide, iteration evidence and individual contribution record | PASS |
| PR publication and planned reviewer request | PR #66 is open; @karimikhaeil review request verified on GitHub | PASS |
| Hosted CI | [PR checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/66/checks); Windows browser job still running at this update | UNVERIFIED |
| Independent review and stakeholder acceptance | requested review is pending; no approval or signoff recorded | UNVERIFIED |

Scope: scalar strings/numbers/integers/booleans/enums/nullable fields and scalar lists,
with bounded range, length and list constraints. Nested objects, references,
patterns, arbitrary unions and other unsupported schema rules fail visibly.
Server validation remains authoritative. Known-key/path checks are not an
arbitrary-secret detector. Synthetic data only. Independent student review,
stakeholder acceptance and Iteration 4 end-to-end acceptance remain separate.

## Correctness pass

Expected outcomes came from the issue acceptance criteria, current SDK metadata
and explicit examples: -1000 is allowed, 1001 exceeds the maximum, 1.5 is not an
integer, duplicate list entries violate uniqueness, false remains a boolean and
an empty required field is invalid. Unicode length uses code points. Unsupported
schema rules fail visibly rather than silently validating an incomplete subset.
The actual backend independently returned `invalid_config` for `amount: 1001`.

The real browser test compares the saved API response's two configurations with
`[{ amount: 42 }, { amount: 7 }]`, compares exported JSON with the entire saved
definition, reloads from SQLite, and checks that an HTTP 409 copy failure retains
the unsaved value 43. This is an API/SQLite integration check. Component tests use
mocked public metadata and diagnostics for loading, retry, malformed/duplicate
versions, typed controls, focus, busy/deleted-node state and unsafe values.

The form, graph state, serialization and diagnostics were reviewed together.
Only a current validation report is passed to form controls. Selection/focus
does not change configuration; deleted nodes cannot be recreated by stale edits.
Backend validation remains authoritative. No API, migration or dependency change.

## Environment and commands

Windows; Node 24.19.0/npm 11.17.0; Python 3.12.10 with hash-verified
`requirements.lock`; locked npm dependencies; Chrome 156.0.8078.36. Real-browser
checks use an isolated SQLite database and the public synthetic Add Constant
block. No stakeholder data or runtime secrets were used.

- `npm run lint`, `npm run format:check`, `npm run typecheck`: passed.
- `npm test -- --maxWorkers=1 --testTimeout=15000`: **95 passed in 13 files**,
  132.46 seconds. The override is local; the default-timeout attempts are recorded
  below. `npm run build`: passed, including TypeScript and the Vite production build.
- `npm run test:standalone` with `LPS_STANDALONE_MODE=preview`, `LPS_PYTHON`
  selecting the locked Python, isolated `LPS_METADATA_PATH` and
  `PLAYWRIGHT_CHROME_PATH` selecting installed Chrome: **4 passed**, 24.4 seconds.
  No HTTP mocks; the configuration case includes the mobile regression checks.
- `npm run test:browser` against the production build: **4 passed**, 21 seconds.
  These shell/navigation/offline/timeout/keyboard cases use mocked HTTP responses.
- `.venv/Scripts/python.exe -m pytest -q --basetemp .venv/pytest-temp`:
  **374 passed**, with 38 existing Starlette/httpx deprecation warnings.
- `python -m ruff check`, `python -m ruff format --check`, `python -m mypy`:
  passed (44 Python source files).
- `python scripts/check_repository.py`, `check_docs.py`, `check_release_plan.py`,
  `python -m unittest discover -s scripts/tests -q` and `git diff --check`:
  passed. Final documentation/repository checks include the new files: 140
  Markdown files and 296 repository files; 34 plan items; 16 script tests passed.

## Failures and fixes

The first browser run could not select the first of two overlapping test nodes
after reopening. The fixture now moves the second node using supported keyboard
controls and fits the view; the focused scenario then passed twice.

Manual narrow-screen inspection found the canvas collapsed in the column flex
layout. Its flex sizing now preserves the declared 560px height below the medium
breakpoint. The real-browser test checks the rendered height, selection/edit
retention and horizontal overflow at 390x844.

The default five-second unit-test timeout was exceeded by DOM-heavy Canvas,
ValidationPanel and App tests on this Windows host. A two-worker rerun still
exceeded five seconds in two tests. Final serial verification records its exact
timeout override below; repository defaults have not been loosened. Earlier
94-test verification passed before the final mobile fix and added safety case.

## Browser demonstration and outstanding acceptance

Codex performed the browser demonstration against the production frontend and
actual API. It exercised an invalid amount 1001, verified the local/backend
messages, clicked the diagnostic and observed input focus, corrected it to 42,
and saved revision 1 of a synthetic pipeline. Final desktop/mobile captures and
verification results are linked below.

Reopened revision 1 in the final build and observed Amount 42. At 390x844, the
canvas measured 560px high, document width 375px (within the 390px viewport), and
the selected field remained editable. The mobile panel and desktop error state
were visually inspected; the temporary viewport override was restored.

- [Desktop validation](../frontend/screenshots/configuration-desktop.png): amount
  1001, matching local/backend field messages and block identity.
- [Desktop configured value](../frontend/screenshots/configuration-valid.png):
  reopened value 42, with the separate missing-input problem still visible.
- [Mobile configuration](../frontend/screenshots/configuration-mobile.png):
  full-width stacked panel, retained value and usable canvas.

The synthetic block still has an unconnected required input. Run correctly stays
disabled for that separate graph problem. The current catalog cannot construct
an all-valid source-to-sink workflow; source blocks, execution and Iteration 4
acceptance are outside #17. No stakeholder demonstration or student signoff is
claimed. Planned independent reviewer: @karimikhaeil; review pending.

AI assistance: Yousef directed delivery. OpenAI Codex implemented the integration,
tests, mobile correction and documentation, reviewed the final requirements/code,
and executed the recorded checks. This was a separate checking method by the
same assistant, not an independent human review.
