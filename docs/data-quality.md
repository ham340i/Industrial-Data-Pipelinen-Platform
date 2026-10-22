# Data-quality blocks

Issue #25 adds four version `1.0.0` entries to `/api/v1/blocks`. Each takes one
`table` input and returns one `table` output. Put quality nodes upstream of
every sink they must guard. See [design and coverage](architecture/data-quality.md).

| ID | Display name | Configuration |
| --- | --- | --- |
| `transform.null_handling` | Null Handling | `policy`: `fill` or `drop`; `columns`: unique names, empty means all; `fill_values`: explicit non-null scalar per selected column for fill |
| `quality.schema_validation` | Validate Schema | `columns`: nonempty list of `{name,dtype,nullable}`; `allow_extra_columns=false`; `required=true` |
| `quality.null_check` | Null Check | `columns`: unique names, empty means all; `max_nulls=0` per selected column; `required=true` |
| `quality.row_count` | Row Count | `min_rows=0`, optional `max_rows`; inclusive boundaries; `required=true` |

Schema Validation and Validate Schema refer to the same implementation, not two
catalog entries. Types are exactly `string`, `integer`, `number`, `boolean`.
No string-to-number, boolean-to-integer, integer-to-number schema widening, or
other silent conversion occurs. Schema Validation checks declared types even
for empty tables. Non-null expectations inspect actual values, so a nullable
declaration with no actual nulls passes. Extra columns fail unless allowed;
column order is retained and does not affect validation. None of the validators
changes data or rewrites its schema.

Null Handling drops a row if **any** selected column is null. Fill replaces only
null values and preserves non-null values, order and duplicate rows. Fill requires
exactly one correctly typed value per selected column. Selected columns become
non-nullable, including empty output; unselected columns keep their original
schema. Overflow or Float64 precision loss is rejected by the shared platform
adapter. Zero, false and empty strings are values, not nulls.

Passing validations report `pass`. A violated required check raises
`quality_failed`, fails the node/run, and prevents downstream sinks from running.
With explicit `required=false`, the violation reports `warning`, passes the
unchanged table through and permits those sinks. Invalid configuration, missing
Null Check/Null Handling columns, invalid input, and cancellation remain errors
even in optional mode. An unrelated graph branch may publish independently;
these checks do not provide a transaction over the entire graph.

Every run emits a `quality` BlockEvent before its normal successful/failed
lifecycle outcome. Required failures also carry `BlockFailure.diagnostics` so
enforcement and diagnostics do not depend on a working logger. Codes, counts,
thresholds, column/type names and at most 20 zero-based row indices are included;
row values and fill values are excluded. Counts include all offending rows, not
only the reported indices. Row Count uses no row samples. Schema mismatch output
is structural; review it before passing sensitive column names to external logs.

For example, `{"max_nulls":1}` passes a column with one null and fails one with
two. `{"min_rows":1,"max_rows":2}` admits exactly one or two rows and rejects
zero or three. `{"policy":"fill","columns":["reading"],"fill_values":{"reading":0}}`
requires an integer or number reading column; it does not coerce a string column.

Preview is intentionally unsupported: a sampled table cannot establish full-input
validity, and returning normal preview tables would expose full rows. Inspect
the structured events/failures from a synthetic local run instead:

```sh
python scripts/demo_data_quality.py
python -m pytest tests/test_quality.py tests/test_quality_execution.py -q
```

UI/E2E integration remains planned for Iteration 4. Main integration depends on
the executor PR #70 and independent student review; no stakeholder approval is
implied. See [verification](testing/issue-25-data-quality.md).
