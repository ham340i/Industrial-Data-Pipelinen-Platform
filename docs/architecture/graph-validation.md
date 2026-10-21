# Graph validation before run — issue #21

Status: implemented on `feature/21-graph-validation`; independent review by @aboudka2003, CI and merge pending. Execution itself belongs to #22.

## Scope

Static execution readiness: can this definition be handed to the executor? It checks topology, port contracts and block configuration against the registered SDK blocks. It never runs blocks, reads data or touches the metadata database. Data-dependent quality checks (row values, file contents, runtime schema drift) remain runtime concerns.

Saving (#14) still accepts incomplete drafts. Validation is a separate, read-only step, so users can save work in progress and see what blocks execution.

## Design

```text
Canvas draft ──(debounced, semantic edits only)──▶ POST /api/v1/pipelines/validate
     ▲                                                     │
     │ display-only highlights                             ▼
ValidationPanel ◀── {valid, diagnostics[]} ◀── app.pipelines.validation.diagnose()
                                                           │
                         PipelineDefinition.validate_registry() raises the first one
```

- **One rule set.** `app/pipelines/validation.py::diagnose` is the only implementation of execution-readiness rules. The API returns all diagnostics; `PipelineDefinition.validate_registry`, the executor gate from #9, now raises the first diagnostic as a `GraphError`. Its existing codes are preserved; block and configuration failures still map to `invalid_block_config`.
- **Topology reuse.** Kahn's algorithm was extracted from `topological_order` into `kahn_order`, which both the model and the validator use. Nodes left unordered by Kahn are then split into strongly connected components (iterative Kosaraju), so only edges that actually lie on a loop are reported, not edges downstream of one.
- **Lenient parsing.** `PipelineDefinition` rejects cycles, duplicates and dangling references at load time, which would hide every other problem. `GraphDraft` has the same fields and field-level rules (identifier pattern, portability boundary, finite layout) without the structural validator, so these become diagnostics instead.
- **The UI does not duplicate rules.** The frontend only places diagnostics: on a connection if `edge_id` is on the canvas, on a node if `node_id` is, otherwise in the panel list. The existing connect-time checks from #15 still prevent obvious mistakes while editing; the backend remains authoritative.
- **Edits are never touched.** Validation reads the Zustand draft and never writes to it. Edge highlighting is computed on display copies (`markEdges`), and selection or position changes do not trigger a new check because the request omits layout.
- **Execution gate.** `Run pipeline` is enabled only when the latest response describes exactly the current graph and is valid. A pending, stale, failed or invalid check keeps it disabled. With no executor yet (#22), a valid Run click explains that execution is not available.

## API contract

`POST /api/v1/pipelines/validate`. This route is not project-scoped: drafts can be validated before they are saved, or without a project.

Request: `{"definition": <schema_version 1 graph>}` (layout optional and ignored).

Response `200`:

```json
{
  "valid": false,
  "diagnostics": [
    {
      "code": "missing_config",
      "message": "Enter a value for 'resource_id'.",
      "node_id": "source-1",
      "edge_id": null,
      "port": null,
      "field": "resource_id"
    }
  ]
}
```

`valid` is true exactly when `diagnostics` is empty. All six keys are always present. Messages say what to fix and never echo configuration values.

`422` uses the standard error envelope (`validation_error`) for requests that are not a version-1 graph at all: malformed JSON, wrong types, an unsupported `schema_version`, credentials or absolute machine paths in configuration. These match the save boundary and are not graph problems.

### Diagnostic codes and order

Diagnostics are grouped in the order below, then sorted by `node_id`, `edge_id`, `port`, `field`, `code` and `message`. The same graph therefore always yields the same list, whatever order its nodes and edges arrive in.

| Group | Code | Located by | Meaning |
|---|---|---|---|
| 1 | `empty_pipeline` | — | No blocks. |
| 1 | `duplicate_node` | node | Repeated node ID (first occurrence is checked further). |
| 1 | `duplicate_edge` | edge | Repeated edge ID. |
| 1 | `dangling_edge` | edge | Connection to a node that does not exist. |
| 1 | `duplicate_connection` | edge, target node | Same ports connected twice. |
| 1 | `dangling_layout` | node | Layout position for a missing node. |
| 2 | `cycle` | edge, source node | Connection lies on a loop (including self-loops). |
| 3 | `block_unavailable`, `version_unavailable`, `invalid_block` | node | Block or exact version is not registered. |
| 4 | `missing_config` | node, field | Required field absent or blank. |
| 4 | `invalid_config` | node, field | Value violates the block's config schema. |
| 4 | `unknown_config` | node, field | Field not declared by the block. |
| 5 | `unknown_port` | edge, node, port | Connection names a port the block lacks. |
| 5 | `incompatible_ports` | edge, target node, port | Kind, cardinality or table schema differs; the message names the column or type. |
| 6 | `input_cardinality` | edge, node, port | Extra connection into a single-valued input (all but the lowest edge ID). |
| 7 | `missing_input` | node, port | Required input has no connection. |

Checks do not cascade: ports of unavailable blocks and edges to missing nodes are not reported again as port or input problems.

## Tradeoffs and decisions to confirm in review

1. **Stateless route, not project-scoped.** It needs no database, and the builder works without a project. Alternative: `POST /projects/{id}/pipelines/{pid}/validate` for saved revisions only. That was rejected because users need feedback before saving.
2. **Automatic, debounced (300 ms) checks** rather than a "Validate" button. Feedback stays current and Run cannot be enabled by a stale result. The cost is one small request per semantic edit; TanStack Query caches identical graphs.
3. **`snake_case` locations** (`node_id`, `edge_id`, `field`) follow the existing API and `BlockFailure` conventions, not the camelCase in the issue's illustrative example.
4. **Empty pipelines are invalid to run**, although `topological_order` accepts them as a graph.
5. **Pydantic constraint messages** are reused for `invalid_config` because they describe the constraint, never the input value. #17's form can show them per field with `fieldMessages`.
6. **Portability violations stay 422.** Reporting them as diagnostics would need a second, looser node model that bypasses the storage boundary.

## Limitations

- The Release 1 catalog only registers `synthetic.add_constant`, whose input is required, so no all-valid pipeline can yet be built in the real UI. A fully valid run waits for the source blocks in #16. The fixture matrix covers valid graphs with test-only source and sink blocks.
- There is no configuration editor yet (#17), so configuration problems can be seen on nodes but only fixed by changing the definition.
- Dangling-edge and duplicate-ID problems cannot be produced by the current editor; they come from imported or hand-edited JSON and are shown in the panel list.

## Code and tests

- Backend: [`app/pipelines/validation.py`](../../app/pipelines/validation.py), [`app/pipelines/models.py`](../../app/pipelines/models.py), [`app/pipelines/api.py`](../../app/pipelines/api.py)
- Frontend: [`frontend/src/api/validation.ts`](../../frontend/src/api/validation.ts), [`frontend/src/state/validation.ts`](../../frontend/src/state/validation.ts), [`frontend/src/ValidationPanel.tsx`](../../frontend/src/ValidationPanel.tsx), [`frontend/src/Canvas.tsx`](../../frontend/src/Canvas.tsx)
- Fixture matrix: [`tests/fixtures/validation/matrix.json`](../../tests/fixtures/validation/matrix.json) — valid, cycle, self-loop, missing input, incompatible types, missing node, missing port, missing/invalid/unknown config, cardinality, unavailable versions, duplicates, empty.
- Tests: [`tests/test_validation.py`](../../tests/test_validation.py), [`frontend/src/state/validation.test.ts`](../../frontend/src/state/validation.test.ts), [`frontend/src/ValidationPanel.test.tsx`](../../frontend/src/ValidationPanel.test.tsx), [`frontend/standalone-tests/validation.spec.ts`](../../frontend/standalone-tests/validation.spec.ts)
- Results: [iteration 2 testing evidence](../iterations/iteration-2/testing-evidence.md#issue-21--graph-validation-before-run)
