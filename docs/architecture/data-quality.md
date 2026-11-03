# Data-quality blocks (#25)

Design recorded before implementation, October 22, 2026. Initially stacked on
executor PR #70; that prerequisite merged into `main` on October 25 as `00d2c91`.
[PR #71](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/71)
received MarcElHaddad1's follow-up approval on October 31, 2026 at 19:46 UTC and
merged into `main` at 20:08 UTC as
[`35ed771`](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/commit/35ed771ff888ad5e7cdf89e577476f0e66215878).

## Decisions

Four registered implementations use the existing single-table SDK contract:
Null Handling, Schema Validation (displayed as Validate Schema), Null Check,
and Row Count. Validation blocks pass the original table through unchanged.
Schema validation compares exact declared types and nullability, including
empty tables. Nullability mismatches carry expected and actual booleans;
non-null expectations additionally report actual null counts and row samples.
Null Handling explicitly fills selected columns or drops rows with any null
in selected columns. Empty column selection means all columns. Fill values
must match declared scalar types; no implicit cast or imputation is performed.

Validation is required by default. A violation raises a structured BlockError,
so the executor fails that node/run and skips its downstream sinks. Setting
required=false explicitly makes violations warnings and allows publication.
An unrelated branch may still run under the executor's existing semantics;
this is a dependency gate, not an atomic transaction over all pipeline sinks.

Diagnostics contain codes, schema names/types, counts, thresholds, and at most
20 zero-based row indices. Each scan counts all matches while retaining only
those 20 samples; auxiliary index storage is independent of the row count.
They never contain row values or configuration
fill values. They are carried by quality BlockEvents and by BlockFailure on
required failures. This reuses the executor's event collection without adding
an alternate executor or treating observational logging as a validation gate.
Preview is disabled: a sampled table cannot establish whole-input validity,
and the existing preview contract would return full rows.

Alternatives rejected: a second ValidateSchema implementation would duplicate
semantics; silently coercing schema mismatches would hide bad data; reporting
violations only through logging would allow a missing/failing log sink to
convert a required failure into success. Diagnostic output tables would add
mandatory graph wiring to every quality node, so events/failures are used.

## Acceptance and checks

| Requirement | Artifact | Meaningful check |
| --- | --- | --- |
| Explicit fill/drop, no coercion | app/blocks/quality.py | null/non-null, empty, typed fill, missing columns, invalid config |
| One Schema Validation / Validate Schema | catalog + quality.py | exact registration, missing/extra/type/nullability, empty schema-bearing table |
| Null Check and Row Count thresholds | quality.py | below/equal/above, zero rows, invalid/duplicate thresholds/columns |
| Pass/fail/warning and safe structured diagnostics | errors/context + quality.py | required fails, optional warns, bounded indices, no values, broken observer |
| Invalid data cannot pass required gate to sink | tests/test_quality_execution.py | real Executor and CSV sink, invalid output absent, warning output present, prior file retained |
| Public discovery and strict configuration | catalog API | four metadata entries, JSON schema and closed config |
| Developer/operator/provenance docs | docs/data-quality.md and contribution/testing records | reconcile final behavior and actual results |

UI acceptance is deferred to Iteration 4, as required by the issue. Both the
executor prerequisite and the reviewed quality implementation are on `main`.
The [verification record](../testing/issue-25-data-quality.md) distinguishes
the passing pre-merge hosted checks, the November 2 current-main checks and
pending UI/stakeholder acceptance. Automated checks do not supply that acceptance.
