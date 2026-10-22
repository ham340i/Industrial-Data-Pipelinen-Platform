# File sources, column transforms and file sinks

Issues #16, #18 and #20 implement nine SDK v1 blocks. They are discoverable in
the builder and executable through `Block.run`. The workbench execution engine
is a later #22 feature; adding a node does not execute it.

## Runtime resources

Supply `BlockContext(run_id, node_id, workspace_root=Path(...))`. Config stores
only a relative `resource_ref`, for example `inputs/readings.csv`. An optional
`resolve_resource` callback may map that reference to a runtime `Path`; the
resolved file must still be inside `workspace_root` and have the correct suffix.
Prepare input files and output parent directories before execution. These blocks
do not create directories or upload files. Absolute/traversal/device paths and
symlink escapes fail. A trusted local workspace owner must prevent concurrent
replacement of directories or symlinks during an invocation.

## Sources

| ID at version 1.0.0 | Format and defaults |
|---|---|
| `source.csv` | Strict comma-separated records, unique nonblank header, matching row widths; strings by default. Empty strings are preserved. Exact `NULL` denotes null; change `null_value` if needed. |
| `source.json` | A JSON array of flat objects, with identical key sets. Object order may differ; output columns follow the first record. Native JSON scalar types and nulls are preserved. Duplicate keys, mixed string/numeric types, nested values and non-finite numbers fail. |
| `source.parquet` | Polars reads scalar columns; Arrow supplies declared nullability. Preserve names/order and values; map integer widths to SDK integer/Int64 and floating widths to SDK number/Float64. Nested, temporal, decimal and binary types fail explicitly. |

Text sources support `encoding`: `utf-8` (default), `utf-8-sig` (BOM), or
`latin-1`. CSV validates records with the proof's strict standard-library parser
before constructing a Polars frame; JSON validates records before constructing
its typed Polars frame. Parquet reads through Polars with a bounded row count.

All sources accept parallel `columns`, `types` and `nullable` lists. Leave all
three empty to use source metadata. Otherwise list every column in source order;
types are `string`, `integer`, `number`, or `boolean`, and nullability contains
booleans. Conversion is explicit and strict. Missing, duplicate or mismatched
columns, conversion failures and nulls in non-nullable fields fail. An empty JSON
array requires these lists; a header-only CSV and a zero-row Parquet retain their
schemas. An entirely empty CSV has no schema and fails.

```json
{"resource_ref":"inputs/readings.csv","encoding":"utf-8","columns":["sensor","reading"],"types":["string","number"],"nullable":[false,true]}
```

Defaults bound eager SDK materialization: `max_bytes=16777216` (16 MiB),
`max_rows=100000`, `max_columns=256`, `max_cells=1000000`. The respective configurable
ceilings are 128 MiB, 1,000,000 rows, 1,000 columns and 2,000,000 cells. These are
development safety budgets, not measured production throughput. Parquet reads
at most the row/cell budget plus one to detect overflow; compressed data can
still consume more memory than its byte size. JSON parsing is byte bounded.
CSV additionally inherits Python's parser field-size limit (normally 128 KiB).
No streaming or hard process memory guarantee is claimed.

## Transforms

Each transform requires one `table` input and returns one `table`. It preserves
row order; inputs are detached by the SDK and are not mutated.

| ID | Configuration | Behavior |
|---|---|---|
| `transform.select` | `columns: ["sensor", "reading"]` | Reuses the proof's Polars selection; order follows the list; require at least one unique existing column. |
| `transform.rename` | `columns: ["reading"]`, `names: ["temperature"]` | Parallel lists; preserve types/nullability/order. Allow simultaneous swaps. Reject missing names or collisions with renamed or untouched columns. |
| `transform.filter` | `column`, `operator`, `value_text` | One typed predicate; operators `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `is_null`, `is_not_null`. No eval or expression execution. |
| `transform.cast` | `column`, `dtype`, `on_error` | Cast to an SDK type. `on_error="error"` fails the block; `"null"` replaces invalid values and declares the target nullable. Other fields retain their schemas. |

Filter `value_text` is the literal value for a string column, and JSON scalar
text for numbers/integers/booleans. Examples: `"12.5"`, `"0"`, `"true"` as config
string values. Null operators ignore `value_text`; other comparisons drop null
rows. Boolean columns support only equality/inequality and null operators.

Casts accept exact lowercase `true`/`false` strings as booleans and numeric
0/1 as booleans. Numeric overflow, fractional float-to-integer truncation,
non-finite output and integer-to-float precision loss are invalid. Floating
parsing follows finite IEEE Float64 semantics. Integers must fit signed Int64;
unsupported input ranges fail before any transformation. Empty inputs retain
their declared output schema. Filtering does not strengthen nullability merely
because this particular result happens to contain no nulls.

## Sinks

`sink.csv` and `sink.parquet` require one `table`. Config contains `resource_ref`
with `.csv`/`.parquet` suffix and `overwrite`: `error` (default) or `replace`.
Write to a temporary sibling and flush before atomic publication. Error mode
uses a hard link for atomic no-clobber creation; replace mode uses same-filesystem
atomic replacement. A filesystem without the required operation fails safely.
Serialization, flush and publication failures remove the temporary file and
leave an existing destination untouched. This is atomic publication, not a
power-loss durability guarantee. Output parents must already exist.

CSV is UTF-8 with a header; `null_value` defaults to `NULL`. A string equal to the
chosen marker fails instead of becoming indistinguishable from null. CSV does
not carry a typed schema: use the reported schema when reading it back. Parquet
stores scalar types and declared nullability. Zero-row results with declared
columns are supported. Sink preview is unsupported and never writes a file.

The `artifact` output is a one-row SDK table: `location` (logical relative
resource), `format`, `row_count`, and `schema_json` (serialized SDK `DataSchema`).
It contains no absolute filesystem location. Dataset governance/query endpoints
remain #28 work. Success is emitted only after complete file publication.

## Errors and demonstration

Failures include `invalid_config`, `workspace_required`, `unsafe_resource`,
`file_unavailable`, `invalid_csv`, `invalid_file`, `file_limit`, `table_limit`,
`schema_required`, `schema_mismatch`, `unsupported_type`, `unsupported_value`,
`missing_column`, `duplicate_column`, `invalid_filter`, `cast_failed`,
`output_exists`, `ambiguous_null`, and `write_failed`. The SDK adds node context;
messages/events omit original exception text and private file locations.

Install the root hash-pinned lock and run:

```sh
python -m scripts.demo_file_blocks
python -m pytest tests/test_file_blocks.py tests/test_transform_blocks.py tests/test_file_policy.py -q
```

The fixed synthetic demo selects two columns, casts readings, renames the value,
filters strictly positive readings and writes both formats in a temporary
workspace. Hand-worked expected output is A=12.5 and D=3.25; the null and negative
readings are removed. The tests read actual output files back and compare each
intermediate result to saved golden records.

See [design and acceptance](../architecture/iteration-2-file-blocks.md) and
[actual verification](../testing/iteration-2-file-blocks.md).
