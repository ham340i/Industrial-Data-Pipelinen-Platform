# Issue 33 validation recovery

This change covers the current Builder validation and configuration flow. It
uses the existing read-only `POST /api/v1/pipelines/validate` contract and the
current draft in the editor store. A response for an older graph cannot mark
or navigate the new one. The Run button remains gated by validation.

## Checks

| Requirement | Check |
| --- | --- |
| Locate configuration problems | The Builder component test activates a diagnostic with Enter and checks focus on the matching input. A block problem without a field focuses the configuration region. The standalone Playwright test exercises an invalid amount, keyboard navigation and correction against the real API. |
| Preserve the draft | The retry test sends the same graph after an injected API failure and asserts the nodes, connections and configuration are preserved. The standalone check retains the same graph after correction. |
| Communicate and recover accessibly | Status and diagnostic text provide non-colour cues. The retry control keeps keyboard focus on the status region while the new check runs. Pipeline-wide notices are readable list entries. |
| Keep internal details private | A failed HTTP check renders the normalized message. The API regression checks that a custom validator cannot expose its supplied value or filesystem path through exception text. Built-in constraint messages retain actionable limits. |

For a manual check, add a Synthetic Add Constant block in Builder. Set Amount
to `1001`, tab to its configuration diagnostic and press Enter. Focus should
return to Amount with the value intact. Set it to `2` and check that the amount
diagnostic clears while any unconnected input remains reported. Disconnect the
local API, edit a setting and let the check fail. Restart the API and use the
Retry pipeline check button. The draft should remain in the editor throughout.

## Local results

The change was tested on Windows against `main` at `5f0f811888e3e857ab9c5545b72710078f0d46ad`
with Python 3.12, Node 24 and the installed Chrome.

- `npm run check --prefix frontend` passed lint, formatting, type checking,
  97 tests and the production build. The test process used a scratch temp
  directory because Vite could not load a harness fixture from the sandbox's
  default path containing `#`.
- `python -m pytest -q tests/test_validation.py tests/test_pipelines.py`
  passed 129 tests. Ruff and mypy passed.
- `npm run test:standalone --prefix frontend -- validation.spec.ts` passed
  with the real local FastAPI server and Chrome. The server reported the
  amount error, Enter focused the matching field, and revalidation after
  correction retained the unrelated missing-input error and the connection.

## Integration still required

- Preview needs the endpoint and structured error contract from #26. Apply
  diagnostics only to the draft snapshot and node that requested preview.
- #29's execute endpoint runs the latest **saved** revision. The Builder checks
  the editable draft. Before #31 wires Run, agree whether to require a matching
  expected revision on the request or expose explicit saved-revision behavior.
- #27's `GET /api/v1/runs/{run_id}` reports the run revision, status and redacted
  per-block failure code and reason. #31 can use that contract to locate a
  failure in a matching graph. If the graph has changed, display the run and
  its revision separately and leave the current draft untouched. Use the
  existing configuration focus path for structured field references when the
  backend supplies them. The current run failure object has no field property.
- Verify bounded preview failures and a real failed execution in the #31
  workflow after wiring the controls. Include an unavailable resource, a
  failure without a node, and a failed run for an earlier revision. Assert
  recovery, keyboard focus and the absence of private values in visible output.

OpenAI Codex implemented and tested this validation slice against the team's
existing contracts. Independent teammate review, preview and run integration,
and stakeholder acceptance remain pending.

## November 9 recovery audit

The follow-up in [PR #81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81)
starts from `daa9ed85f005b95f4aa47a2051feea8a326ebb52`. Main remains
`5f0f811888e3e857ab9c5545b72710078f0d46ad`. It fixes two reproduced gaps:

- A custom Pydantic error could reuse a built-in code and expose its arbitrary
  exception text. Only native errors with safe error types keep their messages.
  Native errors that embed rejected discriminator values or arbitrary exception
  details use the same neutral, field-addressed recovery message. API tests
  cover ordinary custom errors, a reused built-in code and discriminated unions.
- Keyboard diagnostics previously did not move focus when a block version was
  unavailable or its schema was unsupported. Recovery notices now receive
  focus, retain the saved configuration and keep retry controls accessible.

The new API and component regressions failed before their fixes. The existing
numeric-bound diagnostic still names the limit and focuses the Amount input.
No API fields, schema, dependencies or execution behavior changed.

Final local checks on Windows, Python 3.12 and Node 24:

- `npm run check --prefix frontend`: lint, formatting, types, all 99 component
  and unit tests, and production build passed.
- `python -m pytest -q --basetemp generated-data/pytest-nov9-normal`: 708 passed,
  one existing host-dependent symbolic-link test skipped. Ruff lint/format and
  mypy passed for all 75 source files.
- `npm run test:standalone --prefix frontend`: all five real Chrome/FastAPI
  scenarios passed in both development and production-preview modes, including
  configuration save/reopen, file-block schemas,
  pipeline persistence and keyboard validation recovery. The earlier restricted
  focused test passed its case but stalled during process cleanup; the full run
  with normal process access exited successfully.
- Repository, documentation and Release 1 plan checks passed, as did all 16
  repository-tool tests and `git diff --check`. Git Bash syntax checks used
  normal process access; the restricted runner could not initialize MSYS.

The first restricted backend run had seven failures: six synthetic atomic-file
publication cases could not create hard links, and one SQLite URI fixture used
a temporary path containing `#`. A stable temporary path resolved the URI case;
a direct hard-link probe confirmed Windows access denied for the other six.
The unchanged tests passed with normal filesystem access. No product security
setting was changed. An early frontend type check caught a ref-type mismatch;
the final aggregate check above includes its correction.

The original head's eight hosted checks passed, including its Windows retry:
[CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/42538687842)
and [documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/42538687822).
Those runs do not cover this follow-up. Check the PR's current-head results
before review or merge.

## Design and remaining acceptance

Reuse the existing diagnostic shape, editor store and configuration panel.
Validation stays read-only. Avoid a second error framework or guessed preview
and execution contracts. Using custom exception text would be more specific
but can expose private input; a safe field-level message keeps navigation
without that disclosure. Error notices remain keyboard targets even when no
editable field exists. No performance improvement is claimed.

As verified November 9, #17 and #27 are complete, but preview #26 and workflow
integration #31 are open. The saved-revision choice and real preview/run failure
cases above remain required. The validation slice is tested; issue #33 stays
open until those paths and independent review are complete. The planned reviewer
is `menaboulus`; this document does not assert a review request or approval.

## November 11 main reconciliation (UTC)

Updated the existing PR branch from `4203174d00d86539b0328f7f7f4b1436d6986ecf`
with main `ef1ac1a3c04adee43fd76e36e485364a01a26122`. The conflicts were
additive entries in the AI disclosure and contribution registry; both owners'
records were retained. Builder's automatic merge preserves main's saved-run
controls and this PR's current-draft validation, retry and focus behavior.
No additional application behavior, dependency or test expectations changed.

Verification on Windows, Python 3.12.10, Node 24.19.0 and npm 11.17.0:

- `npm run check --prefix frontend`: all 124 tests, lint, formatting, types
  and production build passed.
- `.venv/Scripts/python.exe -m ruff check`, `ruff format --check` and `mypy`
  passed, with 89 source files checked by mypy.
- `.venv/Scripts/python.exe -m pytest -q --basetemp generated-data/pytest-nov11-normal`:
  749 passed and the existing Windows symbolic-link case skipped.
- `npm run test:standalone --prefix frontend`: five real Chrome/FastAPI
  scenarios passed in development and production-preview modes.
- `npm run test:release --prefix frontend`: the real SQL author, validate,
  save, execute, reopen, rerun and structured-failure workflow passed in
  development and production-preview modes.
- `npm run test:browser --prefix frontend`: all four production-shell
  scenarios passed, including keyboard navigation, offline recovery and timeout.
- Repository, documentation and release-plan checks, all 16 repository-tool
  tests and diff whitespace checks passed.

The first restricted backend run had six atomic-publication failures. A direct
hard-link probe returned Windows access denied; the unchanged full suite passed
with normal filesystem access. Git Bash syntax checks likewise needed normal
process access. The Windows Python launcher alias could not start; the installed
Python 3.12 interpreter and a fresh virtual environment were used instead.
Compose and Linux verification require hosted CI because Docker is not installed
on this test host. Check both CI and Documentation workflows and external
statuses on the published commit; prior-head checks do not verify this merge.
`npm ci` reported 14 audit findings in the unchanged frontend dependency lock;
dependency remediation is outside this reconciliation.

Main now supplies saved-run controls and artifact registration/query APIs.
The old statement that no run controls exist is historical. Full preview/run
error-navigation acceptance, independent teammate review and stakeholder
acceptance are still not established by these regression checks. A separate
read-only code review found no merge-induced regression. Main's existing
placeholder Run button remains separate from the real saved-run control; this
reconciliation does not redesign that inherited UI.

OpenAI Codex resolved the conflicts and ran this verification at Yousef's request.
No independent student approval, issue closure or merge to main is claimed.
