# Bounded selected-node preview (#26)

The builder previews unsaved CSV, JSON and Parquet Source output and a linear path of Select Columns transforms. It displays schema, sampled rows, sample-scoped null counts, inspected-row counts and the provenance of full counts. CSV/JSON full counts remain unknown until input completion is observed; Parquet counts come from file metadata. Preview is an explicit user action, separate from normal execution and persistence. SQL/SQLite preview and catalog integration are excluded from this extension by user direction; existing standalone SQL code is unchanged.

## Supported scope

| Block/path | Behavior |
|---|---|
| CSV Source 1.0.0 | Streams a bounded prefix using the configured encoding, null marker and optional schema. No full-file read or execute-and-truncate fallback. |
| JSON Source 1.0.0 | Incrementally reads a bounded prefix of a JSON array of flat records. Uses a configured schema or explicitly sample-derived types. |
| Parquet Source 1.0.0 | Reads bounded batches after footer and declared row-group decoding checks. File metadata supplies schema and full row count. |
| Select Columns 1.0.0 | Projects a bounded upstream table, preserving row order, types, nullability and count provenance. A single supported file source path is required. |
| Synthetic Add Constant 1.0.0 | Retains its SDK preview and reviewed row-preserving policy for compatibility. Its strict input port still applies; no invented input or relaxed schema compatibility. Hidden from new authoring choices. |
| Other transforms, quality gates, sources, triggers and sinks | Unsupported with a public reason. Preview never invokes their execution paths, timers, quality side effects or output publication. |

This is bounded upstream preview for the supported path, not general Run-to-Here. Capability metadata is necessary; the service also checks its audited exact-version policy before reading. Adding preview to another SDK block does not automatically make arbitrary ancestors safe.

## Local workspace setup

Open **Settings** in the sidebar, enter an existing absolute data-folder path on the API computer, and choose **Save workspace**. This validates access and prepares each project's `<root>/<project UUID>/inputs` folder. New projects receive their folders automatically. The saved app setting takes precedence over `LPS_WORKSPACE_ROOT` and applies without an API restart. See [workspace settings](workspace-settings.md) for persistence, environment fallback and reset behavior.

Alternatively, set `LPS_WORKSPACE_ROOT` **in the API process environment** to an existing parent directory. Without an app override, this remains the default. Each project's files live in its own `<root>/<project UUID>/` directory. The UUID is available in the builder URL or projects API. Settings/project creation prepare folders; preview itself never creates directories or uploads input files.

For example, from the repository root in PowerShell, before starting the API:

```powershell
$env:LPS_WORKSPACE_ROOT = Join-Path $PWD.Path 'local-data/workspaces'
# Create <LPS_WORKSPACE_ROOT>/<project UUID>/inputs and place readings.csv there.
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Configure the CSV Source's **Resource Ref** as `inputs/readings.csv`. Leave `columns`, `types` and `nullable` all empty for a string schema from the CSV header, or supply matching lists, for example `columns=["sensor","reading"]`, `types=["string","number"]`, `nullable=[false,true]`.

For JSON or Parquet, use the corresponding source and resource suffix, such as `inputs/readings.json` or `inputs/readings.parquet`. JSON accepts a top-level array such as `[{"sensor":"A","reading":12.5},{"sensor":"B","reading":null}]`. Nested objects/arrays are unsupported. JSON needs an explicit schema for empty arrays or columns containing only nulls in the retained sample. Parquet retains its file schema even when empty. The three schema configuration lists must always have matching lengths.

The existing private `WorkspaceBinding` records may remap a resource ID to a local file. Only bindings belonging to the selected project are consulted. Relative binding targets resolve inside that project's folder; absolute targets must still resolve inside it. Secret-only bindings do not supply a file. No binding or absolute path enters portable pipeline JSON or the preview response. A project directory may not alias another directory through a symlink/junction. File resolution retains the SDK suffix and containment checks.

The workspace owner must prevent concurrent directory/symlink replacement during a read; this is the existing local file policy, not a filesystem sandbox. For containers, mount the data folder into the API container and configure its container path. Environment fallback requires passing the variable into the API; setting it only in a frontend process or a Compose `.env` is insufficient. No workspace setting changes normal run/timer resource resolution in this feature.

## API and validation

`POST /api/v1/projects/{project_id}/pipelines/preview`

```json
{
  "definition": {
    "schema_version": 1,
    "nodes": [{"id":"csv","block_id":"source.csv","block_version":"1.0.0","config":{"resource_ref":"inputs/readings.csv"}}],
    "edges": []
  },
  "node_id": "csv",
  "output_port": "table",
  "limits": {"max_rows":20,"max_cells":2000}
}
```

The request is a semantic draft, with no layout or stored revision required. Strict portable config and field validation apply to the entire envelope. Node and edge identities must be unique globally. Capability, configuration, ports, cardinality and graph diagnostics are checked on the selected ancestor subgraph. Invalid downstream or disconnected nodes do not block this preview; their execution diagnostics remain in Pipeline check. Edges into the ancestor set are included, so dangling inputs and cycles cannot disappear through subsetting.

The response includes `data_schema`, `rows`, `sample_row_count`, `sample_cell_count`, `inspected_row_count`, `full_row_count`, `full_count_scope`, `truncated`, `sampling_method`, `schema_scope`, `null_scope`, `nulls`, `effective_limits`, `source_read_bytes`, `elapsed_ms` and `evaluated_node_ids`. Schema is retained for header-only CSV input. An entirely empty CSV has no usable header and returns a structured error. The updated client requires count provenance; deploy the backend and frontend together.

## Sampling and truthful counts

Sampling takes leading rows in source order. The CSV reader inspects at most the retained row budget plus one data record to distinguish truncation from end-of-file. That lookahead record counts as inspected, but is not returned or included in null summaries. It is checked for width and field-size bounds, not converted against the declared types. Errors beyond this inspected prefix are unknown; a preview is not proof that the full pipeline will execute successfully.

For CSV/JSON, `full_row_count` is present only when input completion was observed (`full_count_scope="observed"`). Otherwise it is `null` with scope `unknown`, even if an extra inspected record happened to be the last record. JSON additionally validates the closing array and trailing whitespace through EOF before claiming completion. Its lookahead is parsed and checked for shape/scalar/field bounds but does not influence inferred types or null summaries. Up to 1 KiB of read-ahead may contain unread tail data; reading bytes is not equivalent to validating them.

For Parquet, `full_count_scope="file_metadata"` labels the footer count, including when the sample is truncated. This is metadata evidence, not a full-data scan. `inspected_row_count` counts rows in the batches delivered to the preview reader, not every row a native codec may decode internally. Row-preserving projections carry source evidence forward. `null_scope` is always `returned_sample`; these counts never imply whole-input quality-gate success.

With no configured CSV schema, columns are strings with conservative `nullable=true`, and `schema_scope="header"`. JSON uses `schema_scope="sample"`, consistent scalar types across retained rows, and conservative nullability; unsampled rows may differ. Parquet uses `schema_scope="file_metadata"` and the file's supported scalar types/nullability. Configured types/nullability produce `schema_scope="declared"` and are enforced on returned rows. Integers outside JavaScript's exact range (absolute value greater than 2^53-1) produce `preview_value_range` instead of silently rounding in the browser; configure a string column to display integers within the SDK's supported integer range exactly.

## Resource policy

| Budget | Enforcement |
|---|---|
| Request body | 256 KiB before JSON parsing; at most five seconds to receive the body |
| Draft | 100 nodes, 200 edges; at most 20 nodes in the selected ancestor path |
| Returned data per step | Defaults: 20 rows / 2,000 cells. Accepted maxima: 1,000 rows / 10,000 cells |
| Source read | At most 2 MiB, lowered by configured source `max_bytes`; one sentinel byte may detect overflow |
| CSV record | At most 64 KiB, including multiline records and header; bounded before parser materialization |
| All file-source shapes | At most 128 columns, lowered by source `max_columns`; column names at most 128 characters; fields at most 4,096 characters |
| JSON parsing | At most 1 KiB read-ahead; 64 KiB per record before JSON decoding; nested containers rejected while framing; duplicate keys rejected by the decoder |
| Parquet metadata | Footer at most 256 KiB before Arrow parsing; Thrift string limit 64 KiB and container limit 10,000; at most 1,024 row groups |
| Parquet decoding | Selected row groups' declared uncompressed column sizes sum to at most 8 MiB, checked before batch decoding; each materialized Arrow batch also checked against 8 MiB before conversion to Python rows |
| Retained source rows | Minimum of requested rows, requested cells divided by source width, source `max_rows`, and source `max_cells` divided by source width |
| Response | At most 2 MiB serialized JSON; oversized responses fail instead of silently truncating |
| Concurrency | Two admitted preview requests per API process; extra requests receive 429 without queuing |
| Service time | Five-second cooperative deadline, checked during reading and between transformations |

Source limits bound inspected/retained work for preview rather than requiring an eager full-file check. For example, a smaller source row limit truncates the preview and leaves full count unknown. Narrowing columns later does not retroactively increase the upstream sample: a wide source may return fewer rows than the selected narrow output's requested limit could hold.

Only one current table is retained between transforms. SDK validation and result construction create bounded copies. Transient allocations are bounded by the request, record, input and table caps; this is **not** a hard process-memory ceiling. The final JSON serialization is checked before sending and may temporarily allocate more than the response ceiling. OS file operations, database access and native conversion cannot be forcibly interrupted by these cooperative checkpoints. A hard wall-clock/RSS guarantee would require worker-process isolation and is not claimed.

Parquet uses a seekable budgeted stream and counts repeated reads, including footer reads, toward the 2 MiB budget. Memory mapping, prefetching and threaded batch reads are disabled. A small requested sample can still be rejected if its containing row group exceeds the declared decoding budget. Native codec allocations occur before the materialized-batch check; metadata checks and output caps do not establish a hard memory boundary against corrupt files. Unsupported formats, excessive metadata or decoding work fail explicitly instead of falling back to full execution.

Client cancellation/disconnect signals the worker; admission capacity remains occupied until it finishes. This avoids unlimited abandoned threads. No executor, normal run/revision records, artifact publication, scheduler or log recorder is used. Every preview response, including errors, sends `Cache-Control: no-store`.

## Frontend state and errors

The panel sits below the canvas/configuration area. The library scrolls within a bounded height so a long catalog does not push preview far down the page. Choose an output and limits, then explicitly Preview/Refresh. Sample, Schema and Null summary tabs support empty results and narrow screens. Unsupported blocks show their declared reason without sending a request.

The preview session key includes project, draft generation, the full semantic definition, selected node, output, limits and execution-busy state. A key change unmounts the session, aborts its request and discards rows immediately. Moving/selecting graph geometry alone does not alter the semantic definition. A new refresh clears the previous result before reading; late replies cannot replace newer state. There are no automatic retries, background refreshes, persisted preview rows or TanStack preview cache entries.

SDK failures use an allowlist of public reasons. API failures carry stable code, node/field/port context where known and a correlation ID. The preview client parses this endpoint's envelope without changing generic Axios behavior elsewhere. The panel offers configuration focus for an affected node and preserves the draft after errors. Input values, private paths and raw exception strings are not error messages or logs.

## Implementation and verification

- Service, contracts and admission: `app/preview/`; API wiring: `app/main.py`; workspace configuration: `app/config.py`.
- SDK observation callback: `PreviewObservation` and `BlockContext.observe_preview`, scoped to one request; CSV reader: `app/blocks/preview_policy.py` and `files.py`; JSON/Parquet readers: `app/blocks/file_preview.py`; projection: `transforms.py`.
- Client/panel: `frontend/src/api/preview.ts`, `frontend/src/state/preview.ts`, `frontend/src/PreviewPanel.tsx`, `Builder.tsx` and capability metadata parsing.
- Regression evidence: [issue #26 verification](../testing/issue-26-preview.md). Broader workflow integration, error UX and performance work (#31/#33/#35) can extend this contract without interpreting sampled counts as full counts.
