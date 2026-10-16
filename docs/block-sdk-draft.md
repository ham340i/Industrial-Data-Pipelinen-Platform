# Block SDK v1 — developer guide

The SDK in `app/blocks/` provides the shared interface for declaring, validating,
running and discovering blocks. It uses typed Python tables and the existing
Pydantic dependency and can be used without starting the API or a database.

This guide covers the SDK and its synthetic extension example from
[issue #8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8).
See the [architecture overview](architecture/block-sdk-release-1.md) and
[proposed ADR-0003](architecture/decisions/ADR-0003-block-sdk-contract.md)
for design decisions. Review and acceptance evidence are maintained separately
in the [verification record](testing/issue-8-block-sdk.md).

## Getting started

Use the public imports from `app.blocks`. The project targets Python 3.12;
run the following example from the repository root using the development
environment and its installed dependencies.

```python
from app.blocks import (
    BlockContext,
    BlockEvent,
    BlockMetadata,
    BlockRegistry,
    PreviewLimits,
    Table,
)
from app.blocks.sample import AddConstantBlock, VALUE_SCHEMA

events: list[BlockEvent] = []
registry = BlockRegistry()
registry.register(AddConstantBlock())
block = registry.resolve("synthetic.add_constant", "1.0.0")
context = BlockContext("synthetic-run", "node-1", log_sink=events.append)

config = {"amount": 3}
inputs = {
    "table": (
        Table(
            data_schema=VALUE_SCHEMA,
            rows=({"value": 2}, {"value": -1}, {"value": 0}),
        ),
    )
}

parsed, checked = block.validate(config, inputs)
assert parsed.model_dump() == config
assert events == []

output = block.run(config, checked, context)["table"][0]
assert isinstance(output, Table)
assert output.rows == ({"value": 5}, {"value": 2}, {"value": 3})

sample = block.preview(
    config, inputs, context, PreviewLimits(max_rows=1)
)["table"][0]
assert isinstance(sample, Table)
assert sample.rows == ({"value": 5},)

metadata = BlockMetadata.from_public(registry.public_metadata()[0])
assert metadata.block_id == "synthetic.add_constant"
assert metadata.version == "1.0.0"
assert [event.event for event in events] == [
    "started", "succeeded", "previewed"
]
```

The [sample implementation](../app/blocks/sample.py) adds a constant to the
integer `value` column. Its `amount` defaults to `1` and accepts integers
from `-1000` to `1000`. It preserves row order and the schema, including
for an empty table.

## Implementing a block

1. Derive a configuration model from `BlockConfig`. Use Pydantic `Field`
   constraints and validators for configuration rules.
2. Subclass `Block[YourConfig]` and assign its `config_model`.
3. Supply a `BlockDescriptor` with identity, named ports and preview capability.
4. Implement `_execute(config, inputs, context) -> PortValues`. Return a mapping
   of declared output names to tuples of payloads.
5. If preview is supported, override `_preview`, set `supports_preview=True`
   and set `preview_reason=None`. Otherwise supply a nonblank unsupported reason;
   the descriptor provides a default reason.
6. Register the instance explicitly and add golden and failure fixtures.

Optional `before_execute` and `after_execute` methods provide lifecycle hooks.
Put data-dependent quality decisions in execution rather than configuration
parsing or lifecycle setup.

Registered instances may be reused across invocations. Keep invocation state
in local variables or context, and maintain deterministic behavior where the
block contract requires it. The SDK does not enforce every implementation's
statelessness or determinism. Use the synthetic block as the complete extension
reference.

## Package responsibilities

| Module | Responsibility |
|---|---|
| [contracts.py](../app/blocks/contracts.py) | Configuration, descriptors, metadata, ports, schemas, payloads and preview limits |
| [base.py](../app/blocks/base.py) | Validation, execution, lifecycle and preview boundaries |
| [context.py](../app/blocks/context.py) | Runtime identities, events and injected callbacks |
| [errors.py](../app/blocks/errors.py) | Structured public failures |
| [registry.py](../app/blocks/registry.py) | Explicit registration, exact version lookup and metadata snapshots |
| [sample.py](../app/blocks/sample.py) | Synthetic Add Constant block |
| [__init__.py](../app/blocks/__init__.py) | Public imports without automatic registration or I/O |

## Public contracts

| Model | Fields |
|---|---|
| `BlockDescriptor` | `sdk_version`, `block_id`, `version`, `block_type`, `name`, `category`, `inputs`, `outputs`, `supports_preview`, `preview_reason` |
| `BlockMetadata` | Descriptor fields plus `config_schema` |
| `BlockConfig` | Block-defined public configuration fields |
| `Column` | `name`, `dtype`, `nullable` |
| `DataSchema` | `columns`, `allow_extra_columns` |
| `Port` | `name`, `kind`, `required`, `many`, `data_schema` |
| `Table` | `data_schema`, `rows` |
| `ControlSignal` | `kind="trigger"` |
| `PreviewLimits` | `max_rows`, `max_cells` |
| `BlockFailure` | `code`, `reason`, `node_id`, `field` |
| `BlockEvent` | `run_id`, `node_id`, `block_id`, `version`, `event`, `error_code` |

The shared model policy uses strict types, rejects unknown fields, enables
default validation and freezes field assignment. Nested dictionaries remain
mutable; invocation boundaries detach and revalidate table values.

Identity and display fields must be nonblank. Column names must be unique within
a schema, and port names must be unique within each input/output direction.
Block types are `trigger`, `source`, `transform`, `quality` and `sink`.

Serialize public models with `model_dump(mode="json")` or `model_dump_json()`.
Tuples become JSON arrays. Read model JSON with `model_validate_json()` and
registry metadata with `BlockMetadata.from_public()`.

## Configuration and defaults

Configuration must be ordinary JSON with string keys and finite numbers.
Arrays are supported; tuples, cycles and runtime objects are rejected.

The same public-JSON policy checks configuration schemas and defaults. Known
credential keys are rejected after normalizing case and punctuation:
`password`, `passwd`, `secret`, `secrets`, `credential`, `credentials`,
`token`, `access_token`, `refresh_token`, `api_key`, `connection_string`,
`dsn` and `username`.

Arbitrary secret strings under other names cannot be detected automatically.
Keep public defaults, descriptions, identities and error reasons free of
sensitive values. Resource identifiers can be public configuration; resource
handles and services belong in the runtime context.

During registration, `BlockConfig.public_schema()`:

1. Checks the shared model policy and generated configuration schema.
2. Evaluates defaults and checks their field annotations and public-JSON values.
3. Probes model validation with an empty configuration.
4. Tolerates missing-required-field errors during that probe and rejects other
   validation errors.

This probe can catch an invalid decorated field-validator default even when
another field is required. It cannot fully evaluate rules needing actual
required-field values, particularly after-model validators. A complete
configuration is validated when supplied for validation, execution or preview.

Preserve the SDK model policy and do not disable default validation on individual
fields. Registration does not comprehensively detect every field-level
`validate_default=False` override, so an author must not rely on registration
to enforce that prohibition.

Validators and default factories must be pure. Factories must be evaluable
without missing required inputs and may run more than once during registration
or metadata generation. Validators used during the empty-configuration probe
must account for required values being absent.

## Ports and table schemas

`PortValues` is a dictionary of declared port names to tuples of `Table` or
`ControlSignal`. Use a tuple even for one payload.

| `required` | `many` | Permitted payload count |
|---|---|---|
| false | false | Zero or one |
| true | false | Exactly one |
| false | true | Zero or more |
| true | true | One or more |

Missing optional ports normalize to empty tuples. Undeclared ports, incorrect
payload types and invalid cardinality are rejected.

Data ports require a `DataSchema`; control ports cannot declare one.
Trigger blocks may emit only control ports.

A concrete table declares every actual column, including for zero rows.
Every row must have exactly those declared keys. Setting
`allow_extra_columns=True` does not permit undeclared keys in a table's rows.

Supported column types are `string`, `integer`, `number` and `boolean`.
Nulls require `nullable=True`. Boolean values do not satisfy numeric columns;
`number` accepts integer or float values, and non-finite numbers are rejected.

### Connection compatibility

Use `ports_compatible(output, input_port)` to compare declared payload kinds
and schema guarantees.

- The output must guarantee every column required by the input.
- Declared types must match exactly. An `integer` schema does not match a
  `number` schema even though number-valued rows can contain integers.
- A nullable output column cannot satisfy a nonnullable input column.
- A strict input requires matching declared column names and an output that
  forbids extra columns.
- An input permitting extras can accept additional output columns.

For matching columns, types and nullability:

| Output permits extras | Input permits extras | Compatible |
|---|---|---|
| false | false | Yes |
| false | true | Yes |
| true | false | No |
| true | true | Yes |

```python
from app.blocks import DataSchema, Port, ports_compatible
from app.blocks.sample import VALUE_SCHEMA

strict_port = Port(name="table", data_schema=VALUE_SCHEMA)
open_port = Port(
    name="table",
    data_schema=DataSchema(
        columns=VALUE_SCHEMA.columns, allow_extra_columns=True
    ),
)

assert not ports_compatible(open_port, strict_port)
assert ports_compatible(strict_port, open_port)
```

Runtime table checks compare a table's fully declared actual columns with the
receiving port contract. This differs from checking the possible outputs of a
declared output port: a concrete table already identifies its actual columns.

Connection compatibility does not validate graph topology or connection counts.
The invocation boundary separately checks payload cardinality.

## Validation and execution

`validate_config(config)` is available on `Block` subclasses and returns their
typed configuration. `validate(config, inputs)` additionally returns detached,
checked inputs without executing the block, invoking lifecycle hooks or emitting
SDK events. Author-provided validators must remain pure.

`run(config, inputs, context)` performs:

1. Descriptor, configuration and input validation.
2. A `started` event and `before_execute`, followed by input revalidation.
3. `_execute`, followed by output validation.
4. `after_execute`, followed by output revalidation and detachment.
5. A `succeeded` event and the validated output mapping.

Expected validation failures use `BlockError`. Unexpected execution exceptions
receive a generic public failure reason. Failure events require a valid block
descriptor; a failure can occur before a `started` event.

## Preview

`preview(config, inputs, context, limits=None)` uses the separate `_preview`
implementation. There is no automatic fallback to `run`, and execution
lifecycle hooks are not invoked. Sink descriptors cannot advertise preview.

| Budget | Default | Maximum accepted value |
|---|---|---|
| `max_rows` | 20 | 1,000 |
| `max_cells` | 2,000 | 10,000 |

Both budgets must be positive. Rows and cells are counted across all returned
tables; cells equal rows multiplied by declared column count. The wrapper
rejects oversized results rather than truncating them.

The synthetic block slices its input before transforming it. Authors must bound
their preview work and avoid publication or other side effects. Returned-data
limits do not provide timeouts, memory isolation or limits on intermediate
allocations.

Successful preview emits `previewed`. Unsupported preview returns its declared
public reason through `preview_unsupported`.

## Runtime context and events

`BlockContext` is a runtime-only frozen dataclass with:

- Nonblank `run_id` and `node_id`.
- Optional `log_sink: Callable[[BlockEvent], None]`.
- Optional `resolve_resource: Callable[[str], Path]`.

Callbacks must be callable when supplied. A block using the resource resolver
must handle its absence and supply safe failures. The host provides the resolver;
the SDK does not implement a resource provider or context export operation.

Events contain run/node identity, block ID/version, one of `started`,
`succeeded`, `failed` or `previewed`, and an optional error code.
They exclude configuration values, table rows and raw exception text.

Logger exceptions do not change execution results or replace original failures.

## Registry and public metadata

Create a `BlockRegistry`, register instances explicitly and resolve an exact
`(block_id, version)` pair. The supported SDK interface version is `1`;
block versions are independent opaque strings. There is no automatic discovery,
latest-version selection or semantic-version fallback.

Registration checks the descriptor, configuration schema, public metadata and
required callable interfaces before changing catalog state. For `Block`
subclasses, advertised preview must have an overridden implementation.
Failed registration leaves the catalog unchanged.

Public metadata contains the descriptor and configuration JSON schema.
It excludes concrete configuration instances, table rows and runtime callbacks.
Registry exports are detached validated snapshots sorted by ID/version.

Resolution rejects changed descriptor contents or a replaced configuration-model
class. It does not detect every change inside implementation code or model
classes.

## Structured failures

`BlockError.failure` is a serializable `BlockFailure`. Using the objects from
the getting-started example:

```python
from app.blocks import BlockError

try:
    block.run({"amount": "3"}, inputs, context)
except BlockError as error:
    failure = error.failure
    assert failure.code == "invalid_config"
    assert failure.node_id == "node-1"
    assert failure.field == "amount"
    print(failure.model_dump_json())
```

| Code | Meaning |
|---|---|
| `invalid_block` | Invalid declaration/default/metadata or changed registered contract |
| `incompatible_sdk` | Unsupported SDK interface version |
| `duplicate_block` | ID/version already registered |
| `block_unavailable` | Unknown block ID |
| `version_unavailable` | Known ID with unavailable requested version |
| `invalid_config` | Invalid or non-public configuration |
| `invalid_inputs` / `invalid_outputs` | Port shape, cardinality, data or schema violation |
| `invalid_context` | Invalid runtime identity or service |
| `invalid_preview_limits` | Invalid preview budget |
| `preview_unsupported` | Preview not advertised or implemented |
| `preview_limit` | Returned sample exceeds the combined output budget |
| `execution_failed` / `preview_failed` | Unexpected execution/preview exception |

Configuration failures omit supplied values and raw Pydantic messages.
Unexpected exceptions in `run` and `preview` use generic public reasons.
Explicit block-authored reasons are public and are not automatically sanitized;
use fixed safe text and stable codes.

Direct validation has no invocation node context. Execution and preview failures
attach the node once a valid context is available. Invalid context is rejected
before that handling, and failures before a valid descriptor cannot emit a
block event.

## Application boundaries

The SDK provides invocation-level contracts and an in-memory registry.
Graph topology, scheduling, persistence, API error mapping and frontend
consumption belong to application services. Resource bindings are supplied by
the host through context callbacks. The synthetic block is an extension example,
not the Release 1 production catalog.

## Testing and verification

Run from the repository root with development dependencies installed in
`.venv`:

```powershell
# SDK tests: allocate a fresh temporary directory for this run.
$pytestRunPath = Join-Path $PWD.Path ('.venv\pytest-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py -p no:cacheprovider --basetemp $pytestRunPath

.\.venv\Scripts\python.exe -m ruff check
.\.venv\Scripts\python.exe -m ruff format --check
.\.venv\Scripts\python.exe -m mypy

# Full backend suite: generate another fresh directory.
$pytestRunPath = Join-Path $PWD.Path ('.venv\pytest-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp $pytestRunPath

.\.venv\Scripts\python.exe -B scripts/check_repository.py
.\.venv\Scripts\python.exe -B scripts/check_docs.py
```

Pytest clears an existing `--basetemp` directory. Reusing a directory whose
earlier files have different Windows permissions can cause `PermissionError`.
Generate the path again for each run; disabling `cacheprovider` avoids the
existing `.pytest_cache`. Temporary directories remain in the ignored
`.venv` folder.

The [golden fixture](../tests/fixtures/blocks/add_constant.json) expects
`[2, -1, 0] + 3` to produce `[5, 2, 3]`.
The [negative fixture](../tests/fixtures/blocks/invalid_configs.json) covers
invalid configuration and expected failure fields.
[Contract tests](../tests/test_blocks.py) cover schemas, ports, registration,
metadata, lifecycle mutations, previews and public failures.

The [verification record](testing/issue-8-block-sdk.md) contains historical
commands, environment and results. Those results describe the recorded working
tree; they do not establish that later changes or the current checkout pass.
Record fresh results for the revision being reviewed. Independent review,
CI and integrated acceptance are separate evidence.

AI assistance is disclosed in the [usage record](ai-usage.md).
