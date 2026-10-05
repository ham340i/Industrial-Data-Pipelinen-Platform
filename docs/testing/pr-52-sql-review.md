# SQL spike PR #52: review findings

Reviewed October 4, 2026 (America/Toronto). [PR #52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52), exact head `5f1f5d67d35f0f013c46934c8d1685406bf79d30`. Author: adamoug; reviewer requested: Al-Yousef. All six hosted checks pass. Existing SQL feature tests pass on Windows/Python 3.12.10: 23 cases. Additional temporary synthetic probes reproduce three incorrect results below. No stakeholder data or live database was used.

## Findings before merge

| Priority / location | Reproduction and impact | Required correction |
|---|---|---|
| P1: [database URI, lines 207-211](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/5f1f5d67d35f0f013c46934c8d1685406bf79d30/app/sources/sql.py#L207) | Create two databases named `data#v1.sqlite3` and `data`, with different synthetic marker values. Configuring the former returns rows from `data`: raw `#` starts a URI fragment, truncates the intended path and consumes the appended `?mode=ro`. A file-existence check on the intended filename does not prevent reading the wrong database or losing the read-only URI option. | Construct the URI from `database_path.resolve().as_uri()` before adding `?mode=ro`. Test `#`, `%` and other valid special filename characters, verify the exact chosen file and retain read-only enforcement. |
| P1: [comment removal, lines 102-115](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/5f1f5d67d35f0f013c46934c8d1685406bf79d30/app/sources/sql.py#L102) | `SELECT 'sensor/*A*/B' AS marker` is rewritten to `SELECT 'sensorB' AS marker` and returns the changed value. `--` inside a quoted literal is similarly treated as a comment and can break a valid query. The preprocessor silently changes data before parameter binding/execution. | Preserve quoted strings/identifiers when inspecting comments, or execute the original SQL with SQLite's read-only authorizer and single-statement enforcement. Add valid quoted comment-text tests alongside real comments and write rejection. |
| P2: [row conversion, lines 187-188](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/5f1f5d67d35f0f013c46934c8d1685406bf79d30/app/sources/sql.py#L187) | `SELECT 'first' AS marker, 'second' AS marker` reports two columns but returns `{'marker': 'first'}`. Converting `sqlite3.Row` to a dictionary collapses duplicate aliases and loses one result, leaving schema and rows inconsistent. | Reject duplicate column names with a clear source error, require unique aliases, or use a positional row contract that preserves both values. Test the selected policy. |

The first probe invocation reproduced all three behaviors but its own temporary setup used a SQLite context manager without explicit close and therefore failed Windows cleanup. Repeating with explicit `contextlib.closing` preserves the same results and completes cleanup successfully. This setup error is not attributed to the PR.

## Other handoff items

- The PR received its issue-derived labels and Iteration 1 milestone during this audit. Its planned reviewer matches issue #12.
- `docs/sql-spike.md` ends inside its Bash command fence; close that fence and finish actual result/review evidence. Documentation checks currently validate links/whitespace, so they do not catch this rendering defect.
- Add the author's own contribution/learning record. The PR body supplies an implementation AI disclosure and explicitly limits stakeholder/production claims; this review does not independently establish those personal claims.
- This review covers the changed SQL module, contract/execution tests and spike document. It does not approve partner access, production SQL security, bounded execution/performance or future source-block integration.

## Review status and AI assistance

Findings are confirmed by source inspection and local synthetic probes; no GitHub approval or completed personal student review is asserted. Codex performed this investigation and prepared the report at Al-Yousef's request. Al-Yousef should understand the findings and verify the author's corrections before approving. Subsequent revisions require rechecking these cases.
