# Issue #26: selected-node preview implementation plan

This records the approved local plan for [issue #26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), including the approved JSON/Parquet extension. The library cleanup, bounded CSV/JSON/Parquet-to-Select previews, project-scoped API, panel and integrated regression tests are implemented locally. The [implemented policy and setup guide](../architecture/selected-node-preview.md) records resolved decisions and supported scope. The live GitHub issue has not been modified, and external review/CI acceptance is not claimed.

The user explicitly excluded SQL/SQLite from the extension. There is no SQL preview, SDK adapter or catalog registration in this work; existing standalone SQL code remains unchanged. Broadening transforms or adding other source formats requires a separate bounded-work policy.

## Delivery status

| Step | Delivered behavior |
|---|---|
| Library cleanup | Example remains in source and runtime registration, hidden from new choices; existing saved graphs remain supported |
| Contracts/API | Strict project-scoped unsaved draft endpoint; schema, sample/null scopes, known/unknown counts and safe structured errors |
| Resource resolution | `LPS_WORKSPACE_ROOT/<project UUID>` plus project-owned private bindings; containment preserved |
| Production preview | Streaming CSV/JSON and bounded Parquet batches, followed by row-preserving Select Columns; no full execution fallback |
| Provenance | CSV header, JSON sample, Parquet metadata or configured schema; full counts explicitly unknown, observed or metadata-derived |
| Limits and side effects | Request/input/record/field/table/response/graph/time/concurrency limits, cooperative cancellation, no sink/timer/run/revision publication |
| Panel | Explicit Preview/Refresh, sample/schema/null tabs, output/limit controls, unsupported/empty/error states and immediate stale-result disposal |
| Verification/docs | Real API browser and unit/integration coverage; setup, sampling/resource policy and [verification evidence](../testing/issue-26-preview.md) |

General Run-to-Here remains outside the supported bounded path, as allowed by the approved plan. No claim of cheap full counts, universal block support or hard process isolation is made.

## 1. Library cleanup and saved-pipeline compatibility

Implemented as the first, independently useful step:

- Keep `app/blocks/sample.py`, its exact ID/version, configuration and execution/preview hooks. Document its single non-nullable integer `value` column and keep SDK contract fixtures/tests.
- Add `library_visible: bool = True` to `BlockDescriptor`; mark the sample `False`. The flag is independent of category and preview capability.
- Keep registration in `app/blocks/catalog.py` and include the full metadata in `GET /api/v1/blocks`. Existing saved nodes must remain recognizable, configurable, connectable, validatable and executable.
- In `frontend/src/api/blocks.ts`, validate the optional flag and accept older catalogs that omit it. In `Canvas.tsx`, filter library/search/drop choices while retaining all metadata for existing nodes. An all-hidden catalog has an explicit empty-library message.
- Use production Row Count blocks in authoring browser tests. Keep separate saved-example compatibility coverage. No pipeline schema change or data migration is needed.

The example demonstrates SDK extension, not bounded file reading or upstream execution. The SDK validates already supplied input before its preview hook. Its small output alone cannot prove bounded production preview.

## 2. Preview request and result contracts

Add dedicated request/response models and a project-scoped draft-preview API in `app/preview/`, wired through `app/main.py`. Proposed route: `POST /api/v1/projects/{project_id}/pipelines/preview`. Confirm existing project/workspace binding conventions before implementing the resolver; the current metadata-path setting is not a data workspace binding.

The request identifies the semantic draft, selected node, output port and requested limits. Preview must work on unsaved semantic edits without creating a pipeline revision or normal run. Check project existence, graph/configuration validity and requested output/capability before reading data. Define which ancestor-only validation failures block preview and present other graph problems separately.

Return declared schema even for an empty sample, bounded rows, sample row/cell counts, effective limits, sampling method and completeness information. Distinguish returned sample size, inspected rows and a known full-input count; unknown full counts stay null. Compute null summaries over an explicitly named scope. A sampled null summary does not establish whole-dataset quality-check success.

The existing SDK preview result is `PortValues`. If counts/completeness need information beyond returned tables, add a typed request-local observation/result contract; avoid shared mutable block state. Preserve structured public error code, reason, node, port/field and correlation context without exposing input values, resource paths or raw exceptions.

## 3. Bounded production preview

The initial CSV/Select implementation is extended to JSON and Parquet. Source hooks remain in `app/blocks/files.py`; `app/blocks/file_preview.py` owns bounded JSON framing and Parquet reading. The service uses explicit exact-version source policies for all three file sources and supports Select Columns after any of them. Capability metadata is enabled only alongside implementation and tests.

- CSV preview needs bounded streaming, including input-byte, column and field-size limits; executing a full source and truncating its result is insufficient.
- JSON frames flat record objects incrementally under byte/record/field limits before standard JSON decoding. Reject nested containers and duplicate keys; infer schema only from retained rows, with conservative nullability. Empty/all-null samples require configured types. A full count requires a validated closing array and EOF.
- Parquet checks footer length before parsing, applies Thrift metadata limits, caps selected row groups' declared uncompressed sizes and reads bounded batches through a seekable byte-budget wrapper. Metadata supplies explicitly labeled schema/count evidence. Native allocation is not a hard RSS guarantee.
- Generalize resource binding, source-root validation and error wording. Extend observation/API/client contracts with schema and count provenance. Preserve the existing panel and ephemeral request lifecycle.
- Retain the SDK output defaults of 20 rows/2,000 cells and maximum accepted limits of 1,000 rows/10,000 cells. Define request/graph size, inspected input, intermediate allocations, response size, concurrency and elapsed-time policies as well. Cooperative cancellation is not a hard process memory/time limit.
- Resolve resources through the project's configured workspace and retain containment checks. Read-only preview must never publish sinks, schedule timers, invoke execution hooks with side effects, or create normal run artifacts/revisions.
- Run-to-Here remains conditional on proving bounds across the supported ancestor subgraph. Otherwise expose supported source/block preview with a clear upstream limitation. Do not substitute arbitrary input or silently execute unsupported ancestors.

SDK preview capability and its unsupported reason remain authoritative. Quality gates, sinks and triggers must explain their limitations. Synthetic Add Constant is not the product acceptance demonstration or a prerequisite for this feature.

## 4. Selected-node panel

Add a typed client (`frontend/src/api/preview.ts`), request state (`frontend/src/state/preview.ts`) and a preview panel integrated with `Builder.tsx`. Extend parsed block metadata with `block_type`, `supports_preview` and `preview_reason` as part of that work.

Place the panel below the canvas with explicit Preview/Refresh controls, output selection where needed, bounded sample/schema/null views and a scope/count explanation. Show no selection, unsupported, loading, empty, success and structured failure states. Do not expose raw schema configuration as a substitute for preview results.

Invalidate results on project, draft generation, semantic graph/configuration, node, output-port or limit changes. Generation alone is insufficient because ordinary semantic edits may not increment it. Cancel obsolete requests and reject late replies using the full request identity. Avoid automatic retries, background refresh and previous-node data while loading. Keep rows ephemeral, out of persisted editor state, logs and long-lived caches; send `Cache-Control: no-store` from the API.

## 5. Verification and related features

| Area | Required evidence |
|---|---|
| Library cleanup | Hidden in browse/search/drop choices; production blocks remain addable; older metadata remains usable; saved sample nodes retain configuration, connections, validation and execution |
| SDK/source limits | Bound reading and intermediate work as well as output; cover empty input, malformed data, wide/large fields, cancellation and unsupported capabilities |
| JSON/Parquet extension | Direct source and Select previews for both formats; sample/metadata provenance; flat-record parsing and encoding; footer/row-group/read caps; no eager execution fallback; unchanged normal file execution |
| Preview service/API | Validate selected output and project/resources; truthful counts/null scope; safe structured errors; no sink writes, timers, run artifacts or pipeline revisions |
| Panel | Selection/configuration races, stale replies, failed refresh, unsupported/empty states, keyboard access and narrow layouts |
| Integrated browser | Use a real CSV fixture and a supported transform; show schema/sample/null scope through the actual API; keep SDK example tests separate |

This touches shared block metadata, graph/configuration validation, project resource resolution, structured API error handling and builder state. Keep normal execution and persistence contracts unchanged unless a specifically reviewed shared-contract change is required. Coordinate with the author/preview/run integration work (#31), actionable error UX (#33) and measured preview performance (#35).

Finish with documented supported blocks, sampling/resource policy and measured verification. Implementation order: library cleanup and compatibility checks, bounded source/service work, supported upstream transforms, panel integration, then integrated tests and documentation. The [library cleanup record](../testing/block-library-visibility.md) records only the first step's verification.

## Assistance

OpenAI Codex implemented the user-approved library cleanup and preview feature, tests and documentation. The user approved the scope; independent code review remains pending. Local verification is recorded separately from acceptance or CI claims.
