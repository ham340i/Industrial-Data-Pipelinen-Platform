import { api, ApiError } from "./client";
import type { Column } from "./blocks";
import type { SemanticDefinition } from "./validation";

export interface PreviewRequest {
  definition: SemanticDefinition;
  node_id: string;
  output_port: string;
  limits: { max_rows: number; max_cells: number };
}
export interface PreviewResult {
  node_id: string;
  output_port: string;
  data_schema: { columns: Column[]; allow_extra_columns: boolean };
  rows: Record<string, string | number | boolean | null>[];
  sample_row_count: number;
  sample_cell_count: number;
  inspected_row_count: number;
  full_row_count: number | null;
  truncated: boolean;
  sampling_method: "leading_rows";
  schema_scope: "declared" | "header" | "sample" | "file_metadata";
  full_count_scope: "unknown" | "observed" | "file_metadata";
  null_scope: "returned_sample";
  nulls: { column: string; null_count: number }[];
  effective_limits: { max_rows: number; max_cells: number };
  source_read_bytes: number;
  elapsed_ms: number;
  evaluated_node_ids: string[];
}
export class PreviewError extends ApiError {
  constructor(
    message: string,
    public readonly code: string,
    status: number,
    public readonly nodeId: string | null,
    public readonly field: string | null,
    public readonly port: string | null,
    public readonly correlationId: string,
  ) {
    super(message, "http", status);
  }
}
// Display only public recovery copy, never arbitrary server exception text.
const recoveryMessages: Record<string, string> = {
  file_unavailable: "Input file is missing or unreadable.",
  unsafe_resource:
    "Resource must be a supported file inside this project's workspace.",
  schema_mismatch: "The sampled data does not match the configured schema.",
  cast_failed: "A sampled value cannot be converted to the configured type.",
  missing_column: "A selected column is absent from the input schema.",
  invalid_csv: "CSV format, encoding, headers or row widths are invalid.",
  preview_columns:
    "Preview requires at most 128 columns with names of at most 128 characters.",
  preview_field_limit: "A preview field exceeds 4096 characters.",
  invalid_json:
    "JSON must be an array of records with unique keys and scalar values.",
  invalid_parquet:
    "Parquet metadata or sampled data is invalid or unsupported.",
  schema_required:
    "Provide an explicit schema for empty or all-null JSON columns.",
  unsupported_type:
    "The sampled columns must have consistent supported scalar types.",
  preview_decode_limit:
    "Parquet metadata or row groups exceed the preview decoding budget. Use smaller row groups or input.",
  preview_read_limit:
    "Preview reached its input-byte or record-size budget. Use a smaller sample or input.",
  preview_limit: "The limits cannot hold a row, or a block exceeded them.",
  invalid_inputs: "The sampled input does not match this block's port schema.",
  invalid_outputs: "The block returned an invalid preview schema or sample.",
  invalid_config: "The block configuration is invalid.",
  unsupported_value: "A sampled value exceeds the supported scalar range.",
  resource_unavailable:
    "The project's resource binding does not provide a file.",
  workspace_required:
    "Configure Workspace in Settings and prepare this project's data folder before previewing.",
  workspace_settings_unavailable:
    "Workspace settings are unavailable. Check Settings and retry.",
  workspace_project_folder:
    "Prepare this project's data folder in Workspace settings.",
  preview_invalid_graph:
    "Check the selected input path and block configuration before retrying.",
  preview_node_missing: "Select a node that exists in the current draft.",
  preview_graph_limit:
    "Preview supports at most 20 nodes on the selected input path.",
  preview_block_unavailable:
    "A block version on the selected input path is unavailable.",
  preview_unsupported: "This input path does not support bounded preview.",
  preview_output_missing: "Select a tabular output on this node.",
  project_not_found: "Project was not found.",
};
const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const count = (v: unknown): v is number =>
  typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const text = (v: unknown, max = 128): v is string =>
  typeof v === "string" && v.length > 0 && [...v].length <= max;
const optional = (v: unknown) => v === null || text(v);
function invalid(): never {
  throw new ApiError(
    "The API returned an invalid preview response. Your draft is unchanged.",
    "invalid-response",
  );
}

export function parsePreview(
  value: unknown,
  request: PreviewRequest,
): PreviewResult {
  if (
    !object(value) ||
    value.node_id !== request.node_id ||
    value.output_port !== request.output_port ||
    !object(value.data_schema) ||
    !Array.isArray(value.data_schema.columns) ||
    value.data_schema.columns.length > 128 ||
    typeof value.data_schema.allow_extra_columns !== "boolean" ||
    !Array.isArray(value.rows) ||
    value.rows.length > request.limits.max_rows ||
    ![
      "sample_row_count",
      "sample_cell_count",
      "inspected_row_count",
      "source_read_bytes",
      "elapsed_ms",
    ].every((k) => count(value[k])) ||
    value.sample_row_count !== value.rows.length ||
    value.sample_cell_count !==
      value.rows.length * value.data_schema.columns.length ||
    (value.sample_cell_count as number) > request.limits.max_cells ||
    (value.inspected_row_count as number) < value.rows.length ||
    typeof value.truncated !== "boolean" ||
    (value.full_row_count !== null &&
      (!count(value.full_row_count) ||
        value.full_row_count < value.rows.length ||
        value.truncated !== value.full_row_count > value.rows.length)) ||
    !["unknown", "observed", "file_metadata"].includes(
      String(value.full_count_scope),
    ) ||
    (value.full_count_scope === "unknown") !==
      (value.full_row_count === null) ||
    (value.full_count_scope === "observed" && value.truncated) ||
    (!value.truncated && value.full_row_count === null) ||
    value.sampling_method !== "leading_rows" ||
    !["header", "declared", "sample", "file_metadata"].includes(
      String(value.schema_scope),
    ) ||
    value.null_scope !== "returned_sample" ||
    !Array.isArray(value.nulls) ||
    !object(value.effective_limits) ||
    value.effective_limits.max_rows !== request.limits.max_rows ||
    value.effective_limits.max_cells !== request.limits.max_cells ||
    !Array.isArray(value.evaluated_node_ids) ||
    value.evaluated_node_ids.length > 20 ||
    !value.evaluated_node_ids.every((id) => text(id)) ||
    value.evaluated_node_ids.at(-1) !== request.node_id
  )
    return invalid();
  const columns = value.data_schema.columns;
  if (
    !columns.every(
      (c) =>
        object(c) &&
        text(c.name) &&
        ["string", "integer", "number", "boolean"].includes(String(c.dtype)) &&
        typeof c.nullable === "boolean",
    ) ||
    new Set(columns.map((c) => c.name)).size !== columns.length
  )
    return invalid();
  for (const row of value.rows) {
    if (!object(row) || Object.keys(row).length !== columns.length)
      return invalid();
    for (const c of columns) {
      const cell = row[c.name];
      if (
        cell === null
          ? !c.nullable
          : c.dtype === "string"
            ? typeof cell !== "string" || [...cell].length > 4096
            : c.dtype === "boolean"
              ? typeof cell !== "boolean"
              : typeof cell !== "number" ||
                !Number.isFinite(cell) ||
                (c.dtype === "integer" && !Number.isSafeInteger(cell))
      )
        return invalid();
    }
  }
  if (
    value.nulls.length !== columns.length ||
    !value.nulls.every(
      (n, i) =>
        object(n) &&
        n.column === columns[i].name &&
        count(n.null_count) &&
        n.null_count ===
          (value.rows as Record<string, unknown>[]).filter(
            (r) => r[columns[i].name] === null,
          ).length,
    )
  )
    return invalid();
  return value as unknown as PreviewResult;
}

export async function previewNode(
  projectId: string,
  request: PreviewRequest,
  signal: AbortSignal,
): Promise<PreviewResult> {
  // Handle this endpoint's allowlisted public envelope before the generic
  // Axios error interceptor discards it. Network/timeout normalization stays shared.
  const response = await api.post<unknown>(
    `/projects/${encodeURIComponent(projectId)}/pipelines/preview`,
    request,
    {
      signal,
      validateStatus: () => true,
    },
  );
  if (response.status >= 400) {
    const envelope = response.data;
    const e =
      object(envelope) && object(envelope.error) ? envelope.error : null;
    if (
      !e ||
      !text(e.code, 64) ||
      !text(e.message, 512) ||
      !text(e.correlation_id, 100) ||
      !optional(e.node_context) ||
      !optional(e.field ?? null) ||
      !optional(e.port ?? null)
    )
      return invalid();
    const nodeId = request.definition.nodes.some(
      (node) => node.id === e.node_context,
    )
      ? (e.node_context as string)
      : null;
    const context = (value: unknown): string | null =>
      typeof value === "string" &&
      /^[A-Za-z_][A-Za-z0-9_.[\]-]{0,127}$/.test(value)
        ? value
        : null;
    throw new PreviewError(
      Object.hasOwn(recoveryMessages, e.code)
        ? recoveryMessages[e.code]
        : "Preview could not complete. Check the input path and configuration, then retry. Your draft is unchanged.",
      e.code,
      response.status,
      nodeId,
      nodeId ? context(e.field) : null,
      nodeId ? context(e.port) : null,
      /^[A-Za-z0-9_-]{1,100}$/.test(e.correlation_id)
        ? e.correlation_id
        : "unavailable",
    );
  }
  return parsePreview(response.data, request);
}
