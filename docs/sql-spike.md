# Issue #12 spike: approved data contracts and safe SQL connectivity

Status: proof-of-concept only. This document records the synthetic contract and safe local SQLite boundary used for the Release 1 SQL-source spike. No partner data, credentials, schema approval, or production connectivity is claimed.

## Scope and intent

This spike validates one small, explicit source contract using synthetic data and a local SQLite database. The goal is to prove that:

- a portable source definition can describe a read-only SQL source without embedded credentials;
- safe parameter binding is used instead of string interpolation;
- a read-only boundary rejects writes, schema changes and unsafe SQL attempts;
- the source contract is explicit enough for future work on issue #23.

This is not a production connector, does not claim Pratt & Whitney Canada access, and does not imply stakeholder approval.

## Synthetic source-to-output contract

The synthetic contract uses a representative measurement table with the following field semantics:

- asset_id: INTEGER, required
- measurement_name: TEXT, required
- measurement_value: REAL, required
- observed_at: TEXT, required; ISO-8601 timestamp
- quality_status: TEXT, required; expected values include valid and review

Example portable config:

```json
{
  "dialect": "sqlite",
  "database_path": "./synthetic_measurements.sqlite3",
  "read_only": true,
  "query": "SELECT asset_id, measurement_name, measurement_value, observed_at, quality_status FROM measurements WHERE asset_id = :asset_id ORDER BY observed_at",
  "parameters": {
    "asset_id": 1001
  }
}
```

The database file is created locally for the proof-of-concept test harness and is not a live partner data source or a production credentialed connection.

Important rules:

- the configuration contains no username, password, token, secret, or credential value;
- database references are local file paths only;
- the query is explicit and constrained to a read-only shape;
- parameters are bound by the database library rather than string concatenation.

## Supported dialect and local proof decision

The supported dialect for this spike is SQLite.

Why SQLite:

- it is available locally with no external infrastructure;
- it is suitable for a bounded proof-of-concept;
- it avoids assuming production database access or partner approval.

This does not mean Pratt & Whitney Canada approves SQLite or that the production connector is SQLite-only. It is a local proof boundary for Release 1 planning and design.

## Read-only and parameter-binding decisions

The local proof uses the following safeguards:

- the SQLite database is opened with `mode=ro`;
- the query must be a `SELECT` or `WITH` statement only;
- multiple statements are rejected;
- write operations such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, and `CREATE` are rejected before execution;
- query values are bound with SQLite parameter binding, not string interpolation;
- a SQLite authorizer denies write and schema-changing actions even if validation is bypassed.

## Open questions for the partner and reviewer

These questions remain unanswered and should be addressed by stakeholders or an authorized reviewer before production implementation:

- Which SQL dialect is actually approved for the real partner source?
- Which source tables or files are approved for testing?
- What is the exact production schema for the source data?
- Are credentials required, and if so, which secret store or access mechanism is approved?
- Is the source on-premises, network-restricted, or air-gapped?
- What approval path is required before any representative sample may be used?
- What retention, audit, and access-review policies apply to the connector?
- Are there any data-handling restrictions around manufacturing measurement data?

These remain explicit open questions; no answers are invented here.

## Limitations and observed failures

This spike has clear limits:

- it proves safe execution against a synthetic local SQLite database only;
- it does not demonstrate access to the Pratt & Whitney Canada source;
- it does not validate production connectivity, authentication, or vendor-specific SQL semantics;
- it intentionally rejects write operations and schema changes as a required safety boundary.

## Follow-up for issue #23

Issue #23 should inherit this contract baseline:

- keep the portable source definition credential-free;
- require read-only execution;
- use safe parameter binding;
- constrain queries to read-only operations;
- treat partner-specific credentials, schema confirmation, and approval as separate decisions rather than assumptions.

## E2E, manual checks, and commands

E2E is not applicable for this tooling-only spike because there is no UI or production execution workflow yet.

Manual verification is done via local pytest checks for the contract and execution boundary.

Run:

```bash
python -m pytest tests/test_sql_source_contract.py
python -m pytest tests/test_sql_source_execution.py
python -m pytest
```

## Result-correctness follow-up: issue #54

Review of PR #52 found three missed correctness cases: unescaped special filename characters could select the wrong database, comment removal changed quoted SQL text, and duplicate aliases lost values during dictionary conversion. The follow-up fixes these without changing the spike's local/synthetic scope.

- Database URI paths are percent-encoded with `Path.resolve().as_uri()` before adding `mode=ro`; a test bypasses all query policy and proves the actual special-filename connection still rejects writes.
- Query inspection masks quoted strings/identifiers and actual comments. SQLite executes the original query, preserving literal values and column names. The bounded SELECT/WITH policy still rejects real unsafe operations and unquoted statement separators; it is not a general SQL parser.
- Duplicate result aliases raise a clear `SqlSourceError` requiring unique aliases, even for an empty result. Distinct aliases, including names differing only by case, retain their positional values.
- The original parameter binding and SQLite authorizer remain. An execution test proves a write attempted inside a SELECT callback is denied and leaves the fixture unchanged.

Actual regression baseline, commands, results, limits and AI attribution are recorded in [the issue #54 verification](testing/issue-54-sql-results.md). Independent student review and integration into PR #52 remain pending; the original contributor's personal claims are not supplied by this follow-up.

