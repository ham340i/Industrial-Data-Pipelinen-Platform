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
