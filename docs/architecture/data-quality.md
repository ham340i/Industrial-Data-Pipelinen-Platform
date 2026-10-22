# Data-quality blocks (#25)

Design recorded before implementation, October 22, 2026. This branch starts
from current main and stacks on PR #70 for its actual executor integration.
Student design/code review by MarcElHaddad1 remains pending.

## Decisions

Four registered implementations use the existing single-table SDK contract:
Null Handling, Schema Validation (displayed as Validate Schema), Null Check,
and Row Count. Validation blocks pass the original table through unchanged.
Null Handling explicitly fills selected columns or drops rows with any null
in selected columns. Empty column selection means all columns. Fill values
must match declared scalar types; no implicit cast or imputation is performed.

Validation is required by default. A violation raises a structured BlockError,
so the executor fails that node/run and skips its downstream sinks. Setting
required=false explicitly makes violations warnings and allows publication.
An unrelated branch may still run under the executor's existing semantics;
this is a dependency gate, not an atomic transaction over all pipeline sinks.

Diagnostics contain codes, schema names/types, counts, thresholds, and at most
20 zero-based row indices. They never contain row values or configuration
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

UI acceptance is deferred to Iteration 4, as required by the issue. Integration
on main is gated by PR #70 and both PRs' independent student review. No customer
or student acceptance is claimed by automated checks.
