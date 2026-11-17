// AI contribution: 50% or more AI-generated
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

type Value = Record<string, unknown>;
type Row = Record<string, unknown>;
interface Shaped extends Value {
  data_schema: Value & { columns: unknown[] };
  rows: unknown[];
  nulls: unknown[];
  truncated: boolean;
}
const COUNT_FIELDS = [
  "sample_row_count",
  "sample_cell_count",
  "inspected_row_count",
  "source_read_bytes",
  "elapsed_ms",
];
const SCHEMA_SCOPES = ["header", "declared", "sample", "file_metadata"];
const FULL_COUNT_SCOPES = ["unknown", "observed", "file_metadata"];
const DTYPES = ["string", "integer", "number", "boolean"];

function evaluatedPath(ids: unknown, nodeId: string): boolean {
  return (
    Array.isArray(ids) &&
    ids.length <= 20 &&
    ids.every((id) => text(id)) &&
    ids.at(-1) === nodeId
  );
}
/** Field types, request echo and fixed protocol values. */
function shaped(value: unknown, request: PreviewRequest): value is Shaped {
  if (
    !object(value) ||
    !object(value.data_schema) ||
    !object(value.effective_limits)
  )
    return false;
  const schema = value.data_schema;
  const limits = value.effective_limits;
  return [
    value.node_id === request.node_id,
    value.output_port === request.output_port,
    Array.isArray(schema.columns) && schema.columns.length <= 128,
    typeof schema.allow_extra_columns === "boolean",
    Array.isArray(value.rows) && value.rows.length <= request.limits.max_rows,
    COUNT_FIELDS.every((k) => count(value[k])),
    typeof value.truncated === "boolean",
    value.sampling_method === "leading_rows",
    SCHEMA_SCOPES.includes(String(value.schema_scope)),
    value.null_scope === "returned_sample",
    Array.isArray(value.nulls),
    limits.max_rows === request.limits.max_rows,
    limits.max_cells === request.limits.max_cells,
    evaluatedPath(value.evaluated_node_ids, request.node_id),
  ].every(Boolean);
}
/** The full count, its scope and truncation must tell one consistent story. */
function totalConsistent(value: Shaped, rows: number): boolean {
  const full = value.full_row_count;
  const scope = value.full_count_scope;
  const truncated = value.truncated;
  const fullValid =
    full === null || (count(full) && full >= rows && truncated === full > rows);
  return [
    fullValid,
    FULL_COUNT_SCOPES.includes(String(scope)),
    (scope === "unknown") === (full === null),
    !(scope === "observed" && truncated),
    truncated || full !== null,
  ].every(Boolean);
}
function countsConsistent(value: Shaped, request: PreviewRequest): boolean {
  const rows = value.rows.length;
  const cells = value.sample_cell_count as number;
  return (
    [
      value.sample_row_count === rows,
      cells === rows * value.data_schema.columns.length,
      cells <= request.limits.max_cells,
      (value.inspected_row_count as number) >= rows,
    ].every(Boolean) && totalConsistent(value, rows)
  );
}
const validColumn = (c: unknown): c is Column =>
  object(c) &&
  text(c.name) &&
  DTYPES.includes(String(c.dtype)) &&
  typeof c.nullable === "boolean";
function columnsValid(columns: unknown[]): columns is Column[] {
  return (
    columns.every(validColumn) &&
    new Set(columns.map((c) => (c as Column).name)).size === columns.length
  );
}
function cellValid(cell: unknown, c: Column): boolean {
  if (cell === null) return c.nullable;
  if (c.dtype === "string")
    return typeof cell === "string" && [...cell].length <= 4096;
  if (c.dtype === "boolean") return typeof cell === "boolean";
  return (
    typeof cell === "number" &&
    Number.isFinite(cell) &&
    (c.dtype !== "integer" || Number.isSafeInteger(cell))
  );
}
function rowsValid(rows: unknown[], columns: Column[]): rows is Row[] {
  return rows.every(
    (row) =>
      object(row) &&
      Object.keys(row).length === columns.length &&
      columns.every((c) => cellValid(row[c.name], c)),
  );
}
function nullsValid(nulls: unknown[], columns: Column[], rows: Row[]): boolean {
  return (
    nulls.length === columns.length &&
    nulls.every(
      (n, i) =>
        object(n) &&
        n.column === columns[i].name &&
        count(n.null_count) &&
        n.null_count === rows.filter((r) => r[columns[i].name] === null).length,
    )
  );
}

export function parsePreview(
  value: unknown,
  request: PreviewRequest,
): PreviewResult {
  if (!shaped(value, request) || !countsConsistent(value, request))
    return invalid();
  const columns = value.data_schema.columns;
  if (
    !columnsValid(columns) ||
    !rowsValid(value.rows, columns) ||
    !nullsValid(value.nulls, columns, value.rows)
  )
    return invalid();
  return value as unknown as PreviewResult;
}

type PublicError = Value & {
  code: string;
  message: string;
  correlation_id: string;
};
/** The error envelope, only when every field is within its public bounds. */
function publicError(envelope: unknown): PublicError | null {
  const e = object(envelope) && object(envelope.error) ? envelope.error : null;
  if (!e) return null;
  const valid = [
    text(e.code, 64),
    text(e.message, 512),
    text(e.correlation_id, 100),
    optional(e.node_context),
    optional(e.field ?? null),
    optional(e.port ?? null),
  ].every(Boolean);
  return valid ? (e as PublicError) : null;
}
const contextName = (value: unknown): string | null =>
  typeof value === "string" && /^[A-Za-z_][A-Za-z0-9_.[\]-]{0,127}$/.test(value)
    ? value
    : null;
function previewFailure(
  status: number,
  envelope: unknown,
  request: PreviewRequest,
): never {
  const e = publicError(envelope);
  if (!e) return invalid();
  const nodeId = request.definition.nodes.some(
    (node) => node.id === e.node_context,
  )
    ? (e.node_context as string)
    : null;
  throw new PreviewError(
    Object.hasOwn(recoveryMessages, e.code)
      ? recoveryMessages[e.code]
      : "Preview could not complete. Check the input path and configuration, then retry. Your draft is unchanged.",
    e.code,
    status,
    nodeId,
    nodeId ? contextName(e.field) : null,
    nodeId ? contextName(e.port) : null,
    /^[A-Za-z0-9_-]{1,100}$/.test(e.correlation_id)
      ? e.correlation_id
      : "unavailable",
  );
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
  if (response.status >= 400)
    previewFailure(response.status, response.data, request);
  return parsePreview(response.data, request);
}
