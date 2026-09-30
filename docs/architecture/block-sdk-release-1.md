# Release 1 Block SDK contract plan

Status: planned contract scope for I1-05. The implementation owner must publish a reviewed interface and fixtures before downstream block implementations finalize. No SDK is implemented here.

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
