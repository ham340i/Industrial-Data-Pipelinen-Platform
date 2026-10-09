# Release 1 Block SDK contract plan

Status: the issue #8 SDK scope is implemented in `app/blocks/`, following the user-approved interface plan, with a synthetic block and contract fixtures. See the [SDK guide](../block-sdk-draft.md) and [verification record](../testing/issue-8-block-sdk.md). Independent designated-reviewer approval, PR/CI evidence and later integrated acceptance are not claimed here.

| Contract area | Required behavior |
|---|---|
| Identity | Stable identifier, block type, human-readable name, version and category |
| Ports | Named typed inputs/outputs, cardinality/required flags, separate trigger/control semantics |
| Configuration | Pydantic-compatible schema, safe defaults and field-specific validation errors |
| Data schema | Explicit expected and produced columns/types/nullability; propagation and runtime checks |
| Runtime metadata | Run/node identity, block version, capabilities and non-secret context |
| Validation | Static config/connection checks separate from data-dependent quality evaluation |
| Execution | Deterministic block invocation with typed tabular inputs/outputs and lifecycle hooks |
| Preview | Discoverable optional capability, bounded schema/sample output, unsupported reason and no sink publication |
| Errors/logging | Stable structured code/reason/node/field context; redact secrets and sensitive rows |
| Fixtures/docs | Golden synthetic fixtures, failure cases, usage/config documentation and extension example |
| Serialization | JSON-safe public registry metadata and configuration; never serialize credentials or runtime handles |

## Issue #8 implementation boundary

SDK v1 uses typed Python tables/control values and existing Pydantic models.
`BlockConfig` supplies strict public config/default validation; `BlockMetadata`
formalizes descriptor/config-schema serialization. The registry resolves exact
ID/version pairs, validates registration atomically and exports detached metadata.
Block wrappers validate inputs/outputs, provide lifecycle/context/log hooks and
separate optional preview with combined row/cell limits. The Add Constant sample
proves deterministic headless extension through synthetic fixtures.

The issue owns these contracts and one synthetic sample, not the full Release 1
block catalog below. No new dependencies, processing libraries, providers,
execution engine, API/frontend changes or database migrations are required for
these five acceptance criteria. Downstream integration remains separate work.

New blocks register against this interface; the engine resolves them by identity/version without special-case React dependencies. A synthetic sample block must prove the extension mechanism.

## Required registry coverage

- Triggers: Manual, bounded Timer.
- Sources: CSV, JSON, Parquet, SQL.
- Transforms: Select Columns, Rename Columns, Filter, Cast, Null Handling, Join, Aggregate, Sort.
- Quality: Schema Validation (also shown as Validate Schema), Null Check, Row Count.
- Sinks: Parquet, CSV.

Schema Validation is one implementation used wherever schema validation is requested. Select/CSV/Parquet prototype code is reused and hardened, not rebuilt under duplicate issues. The resulting registry has 19 distinct block types; REST and advanced industrial connectors are not Release 1 commitments.

## Contract tests required

Verify public metadata/config JSON round-trips; typed-port compatibility; valid/invalid config; deterministic output; input/output schema behavior; optional preview limits; structured failures; redacted logging; and missing/incompatible block-version behavior. Each block owner adds golden and negative fixtures in addition to shared SDK tests.

## Limitations

Registration probes an empty configuration. Validators requiring actual required-field values, particularly after-model validators, cannot be fully checked until a complete configuration is supplied.