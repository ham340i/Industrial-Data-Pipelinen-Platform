# Iteration 2 file blocks: design and acceptance

Issues: #16 (sources), #18 (transforms), #20 (sinks). Design recorded before
implementation. Reuse the SDK/port/Polars selection approach and exclusive-write
semantics from `experiments/headless_etl`; retain that historical proof unchanged.

One reviewable integration change covers these three closely related stories.
The shared scalar-table adapter and workspace policy must agree across readers,
transformations and writers. Existing issue owners remain assigned; the author
does not claim their implementation or independent approval.

## Boundaries and alternatives

- Register three sources, four transforms and two sinks in the existing catalog.
- SDK v1 supports string/integer/number/boolean with explicit nullability. Reject
  unsupported nested, temporal, binary and non-finite values instead of silently
  converting them. Preserve Parquet's scalar values, column names/order, SDK
  type mapping and declared nullability; integer widths normalize to Int64 and
  floating widths to Float64. Schema overrides are checked explicitly.
- Config contains a relative `resource_ref`, never a private absolute path. A
  runtime-only workspace root constrains both a resolver callback and direct
  relative resources. Reject traversal, symlink escapes and unsupported suffixes.
  The workspace owner is trusted; concurrent malicious filesystem replacement
  is outside this local application's threat model.
- Bounded, eager SDK tables are the existing contract, not a streaming engine.
  Limit bytes, rows, columns and cells. Parquet reads at most the row budget plus
  one; JSON is byte bounded before parsing. Runtime engine work remains #22.
- Flat scalar/list configurations remain editable by the existing builder.
  Schema columns/types/nullability and rename source/target lists are parallel
  validated lists; reject duplicates, missing names and length mismatches.
- Filter supports one structured predicate with a finite operator set. No eval,
  arbitrary expression parser or Python execution. Null comparisons use explicit
  is-null/is-not-null operators; other comparisons drop null rows.
- Cast errors fail by default; an explicit null policy makes failed values null.
  Reject numeric truncation and require callers to allow resulting nullability.
- Sinks write and flush a temporary sibling before publication. Error policy uses
  an atomic hard-link create; replace policy uses atomic replace on the same
  filesystem. Fail safely where atomic publication is unsupported. Clean partial
  files; never delete an existing destination after a failed write.
- Sinks return an SDK artifact table with relative location, format, rows and
  serialized schema. Governed dataset endpoints remain #28. No sink preview.

## Acceptance and checks

| Requirement | Artifact | Meaningful check |
|---|---|---|
| #16 registered CSV/JSON/Parquet, schema and encodings | source blocks/catalog | each reader via SDK; golden rows and declared schema |
| #16 missing/unreadable/malformed/empty/unsupported inputs | source tests | missing files, invalid JSON/CSV/encoding, zero rows, nested values |
| #16 bounded workspace access | shared file policy | traversal/absolute/resolver escape/symlink/size/row/cell cases |
| #18 four registered Polars transforms | transform blocks/catalog | per-block golden rows, schema and stable order |
| #18 safe filters, cast and column errors | transform tests | invalid operators/types, nulls, missing/duplicate columns, overflow/loss |
| #20 CSV/Parquet publication and metadata | sink blocks | read back actual files; empty and all scalar types; schema/row metadata |
| #20 overwrite and cleanup | sink tests | existing target, replacement, write/link/replace failure, temporary cleanup |
| shared integration | pipeline fixture/demo | source → all four transforms → both sinks, hand-worked expected rows |
| builder compatibility | catalog/config integration | real exported schemas accepted and configs validated |
| regression/platform | repository quality gates | Ruff, mypy, pytest, docs/repository and hosted Linux/Windows checks |
| review and later UI execution | PR/issue records | independent reviewers requested; #22/Iteration 4 execution pending |

Verification states and actual commands belong in the accompanying testing
record. No stakeholder acceptance or human review is asserted by this design.

AI Assistance: Yousef directed the work. Codex drafted this design and will
implement/run the documented checks; independent teammate review is pending.
