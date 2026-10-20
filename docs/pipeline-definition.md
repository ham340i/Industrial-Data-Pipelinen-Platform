# Portable pipeline definition v1

Issue #9 introduces `app/pipelines/` on top of the reviewed Block SDK in PR #59.
SDK PR #59 is merged in main at `80f8dc7`; the #8 dependency is available. This module
authors and validates definitions; execution and the visual editor remain later
work. Importing the module starts no API, database, or block execution.

## JSON contract

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "source",
      "block_id": "example.source",
      "block_version": "1",
      "config": {"resource_id": "measurements"}
    },
    {
      "id": "transform",
      "block_id": "synthetic.add_constant",
      "block_version": "1.0.0",
      "config": {"amount": 3}
    }
  ],
  "edges": [
    {
      "id": "connection",
      "source": {"node_id": "source", "port": "table"},
      "target": {"node_id": "transform", "port": "table"}
    }
  ],
  "layout": {"positions": {"source": {"x": 10, "y": 20}}}
}
```

`example.source` is illustrative, not an installed production source. The tests
register a synthetic source descriptor for headless integration. Node and edge
IDs use letters/digits plus underscores, periods and hyphens, up to 128
characters, starting with a letter or digit. Block IDs/versions follow SDK rules
and resolve exactly. Ports are named references, not duplicated declarations.

Version 1 is currently the only supported schema version; boolean, string and
floating-point substitutes are rejected. Unsupported versions need an explicit
future migration. Unknown fields are rejected. `nodes` and `edges` default to
empty arrays; config defaults to an empty object. Node/edge IDs are unique within
their respective namespaces. Duplicate endpoint-to-endpoint connections fail.

## Loading, exporting and ordering

```python
from app.pipelines import PipelineDefinition

graph = PipelineDefinition.from_json('{"schema_version":1,"nodes":[],"edges":[]}')
assert graph.topological_order() == ()
authoring_json = graph.to_json()
semantic_json = graph.to_json(include_layout=False)
assert PipelineDefinition.from_json(authoring_json) == graph
```

`to_dict()` produces a detached portable object suitable for
`PipelineRevision.definition`. No schema migration is required. `to_json()`
sorts object keys for stable repeated serialization; node/edge array order is
preserved. This is not a canonical graph hash. Scheduling instead chooses the
lexicographically smallest currently ready node ID and is independent of array
order. Multiple edges between two nodes create one dependency. Both data and
control edges participate in topology; trigger execution belongs to the engine.

Layout affects neither compatibility nor order. Position coordinates must be
finite, and positions must refer to existing nodes. Moving a node changes an
authoring export but not a semantic export. Empty/disconnected DAGs are valid;
cycles, self-loops and dangling nodes are rejected at load time.

## SDK integration

Call `graph.validate_registry(registry)` on a complete graph before execution.
It returns the deterministic order after checking exact block versions, typed
configuration, named ports, data/control separation, schema compatibility and
input connection counts. It performs no execution, preview or SDK event logging.
Validators must remain pure, as required by the SDK.

Required inputs must be connected. Single inputs accept at most one connection;
many inputs permit multiple connections. Many outputs cannot feed single inputs.
These are static guarantees; actual payload cardinality is checked by the SDK
when the later engine invokes a block. A source with no required inputs can be
an independent root. An incomplete draft can be structurally stored, but will
fail complete registry validation until its required connections exist.

Registry validation raises `GraphError` with `code` and optional `node_id`.
Structural/model errors surface as Pydantic `ValidationError`; schema-version
errors do too. API adapters should normalize these errors rather than exposing
raw Pydantic inputs, which can contain rejected sensitive configuration.

## Portability

Use logical `resource_id` values in config. Known credential keys and local path
fields, absolute Windows/POSIX/UNC paths, file URIs, nonfinite numbers, tuples,
cycles and runtime objects are rejected. SDK and existing metadata guards are
both applied. Valid null/boolean/numeric/string/list/object config values survive
round-trips. The guards are bounded policies, not general secret detection.
Review public strings and never export real credentials under arbitrary keys.

Models freeze field assignment, but nested dictionaries remain mutable.
Export and registry validation check original layout key types before JSON can
coerce them (e.g. integer `1` into node ID `"1"`). These checks also apply when
layout is omitted from semantic output. They revalidate config, and returned dictionaries are
detached. Do not treat `model_construct()` or `model_copy(update=...)` as trusted
validation paths. Use normal model construction or JSON loading at boundaries.

See [ADR-0004](architecture/decisions/ADR-0004-portable-dag.md),
[tests](../tests/test_pipelines.py), and
[verification](testing/issue-9-portable-dag.md).

AI Assistance: Codex drafted this module and guide at Karim's instruction.
