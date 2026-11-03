# Iteration 3 Demonstration

Status: Scoped synthetic headless #25 demonstration executed by Codex on
November 2, 2026. Live team/stakeholder iteration demonstration: Not Yet
Demonstrated.

## Demo Objective

Show that the same incomplete input prevents downstream publication when
validation is required and emits a warning when explicitly optional.

## Preconditions

Revision `e03177334f7a89b1d6ca4560e849884a8a22e532`; Windows/Python 3.12.10;
dependencies installed from `requirements.lock`. Normal local file access is
required. The script creates and cleans isolated temporary synthetic files.

## Startup Commands

From the repository root using the prepared environment:

```sh
python scripts/demo_data_quality.py
```

No server or browser is started for this headless demonstration.

## Demonstration Steps

The script creates a CSV with one integer column containing one null, then runs
CSV Source -> Null Check -> CSV Sink twice with `max_nulls=0`. The only policy
change between runs is `required=true` versus `required=false`.

## Expected Behavior

Hand calculation: one null exceeds zero. Required mode must fail the run, skip
the sink and create no output. Optional mode must complete, publish the
unchanged data and report a warning. Both diagnostics must report count one,
maximum zero and zero-based row index zero without exposing cell values.

## Actual Observed Behavior

```text
required=True: run=failed, sink=skipped, published=False
required=False: run=completed, sink=completed, published=True
```

Both structured diagnostics reported `code=null_count`, `observed=1`,
`maximum=0`, `row_indices=[0]`; status was `fail` and `warning`, respectively.
The script's assertions passed with normal local file access.

## Known Limitations

An initial restricted-file-access execution failed its optional-publication
assertion; the unchanged script passed with normal local process access.
This demonstrates backend policy only. Browser UI/E2E acceptance belongs to
Iteration 4; no live student/customer demonstration, full iteration signoff or
performance claim is supplied. Other validators, prior-file preservation and
literal output contents are covered by the [automated cases](testing-evidence.md).

## Issues Demonstrated

[Issue #25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25),
implemented in approved/merged
[PR #71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71).

## Evidence

[Verification and acceptance mapping](../../testing/issue-25-data-quality.md),
[source script](../../../scripts/demo_data_quality.py) and
[contribution/AI disclosure](../../individual-contributions/Al-Yousef-iteration-3.md).
The script is nonvisual; no UI screenshot is claimed.
