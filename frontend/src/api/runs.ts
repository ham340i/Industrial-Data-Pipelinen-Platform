import { api, ApiError } from "./client";
import { isProjectId } from "./projects";

export type RunState =
  "queued" | "running" | "succeeded" | "failed" | "cancelled";
export interface RunFailure {
  code: string;
  reason: string;
}
export interface RunSummary {
  schema_version: 1;
  id: string;
  project_id: string;
  pipeline_id: string;
  pipeline_revision_id: string;
  revision: number;
  state: RunState;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  row_count: number | null;
  error: RunFailure | null;
}
export interface RunBlock {
  position: number;
  node_id: string;
  block_id: string;
  block_version: string;
  state: "queued" | "running" | "completed" | "failed" | "skipped";
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  rows_in: number | null;
  rows_out: number | null;
  error: RunFailure | null;
}
export interface RunEvent {
  sequence: number;
  created_at: string;
  level: "info" | "warning" | "error";
  node_id: string | null;
  kind: string;
  code: string | null;
  message: string;
}
export interface RunDetail extends RunSummary {
  blocks: RunBlock[];
  events: RunEvent[];
}
const states = ["queued", "running", "succeeded", "failed", "cancelled"];
const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const count = (v: unknown): v is number =>
  Number.isSafeInteger(v) && Number(v) >= 0;
const measurement = (v: unknown) => v === null || count(v);
const date = (v: unknown) =>
  typeof v === "string" && Number.isFinite(Date.parse(v));
const optionalDate = (v: unknown) => v === null || date(v);
const failure = (v: unknown) =>
  v === null ||
  (object(v) && typeof v.code === "string" && typeof v.reason === "string");
function invalid(): never {
  throw new ApiError(
    "The API returned unsupported or mismatched run evidence. Refresh to try again.",
    "invalid-response",
  );
}
function summary(
  v: unknown,
  projectId: string,
  pipelineId: string,
): RunSummary {
  if (
    !object(v) ||
    v.schema_version !== 1 ||
    typeof v.id !== "string" ||
    !isProjectId(v.id) ||
    v.project_id !== projectId ||
    v.pipeline_id !== pipelineId ||
    typeof v.pipeline_revision_id !== "string" ||
    !isProjectId(v.pipeline_revision_id) ||
    !count(v.revision) ||
    v.revision < 1 ||
    !states.includes(String(v.state)) ||
    !date(v.created_at) ||
    !optionalDate(v.started_at) ||
    !optionalDate(v.ended_at) ||
    !measurement(v.duration_ms) ||
    !measurement(v.row_count) ||
    !failure(v.error)
  )
    return invalid();
  return v as unknown as RunSummary;
}
export async function listRuns(
  projectId: string,
  pipelineId: string,
  signal?: AbortSignal,
): Promise<RunSummary[]> {
  const { data } = await api.get<unknown>("/runs", {
    params: {
      project_id: projectId,
      pipeline_id: pipelineId,
      limit: 20,
      offset: 0,
    },
    signal,
  });
  if (
    !object(data) ||
    !Array.isArray(data.items) ||
    data.items.length > 20 ||
    data.limit !== 20 ||
    data.offset !== 0 ||
    !count(data.total)
  )
    return invalid();
  const items = data.items.map((v) => summary(v, projectId, pipelineId));
  if (new Set(items.map((v) => v.id)).size !== items.length) return invalid();
  return items;
}
export async function getRun(
  projectId: string,
  pipelineId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<RunDetail> {
  const { data } = await api.get<unknown>(
    `/runs/${encodeURIComponent(runId)}`,
    { signal },
  );
  const result = summary(data, projectId, pipelineId);
  if (
    !object(data) ||
    result.id !== runId ||
    !Array.isArray(data.blocks) ||
    !Array.isArray(data.events)
  )
    return invalid();
  const ids = new Set<string>();
  for (const b of data.blocks) {
    if (
      !object(b) ||
      typeof b.node_id !== "string" ||
      ids.has(b.node_id) ||
      typeof b.block_id !== "string" ||
      typeof b.block_version !== "string" ||
      !count(b.position) ||
      !["queued", "running", "completed", "failed", "skipped"].includes(
        String(b.state),
      ) ||
      !optionalDate(b.started_at) ||
      !optionalDate(b.ended_at) ||
      !measurement(b.duration_ms) ||
      !measurement(b.rows_in) ||
      !measurement(b.rows_out) ||
      !failure(b.error)
    )
      return invalid();
    ids.add(b.node_id);
  }
  let previous = -1;
  for (const e of data.events) {
    if (
      !object(e) ||
      !count(e.sequence) ||
      e.sequence <= previous ||
      !date(e.created_at) ||
      !["info", "warning", "error"].includes(String(e.level)) ||
      !(e.node_id === null || typeof e.node_id === "string") ||
      typeof e.kind !== "string" ||
      !(e.code === null || typeof e.code === "string") ||
      typeof e.message !== "string"
    )
      return invalid();
    previous = e.sequence;
  }
  return {
    ...result,
    blocks: data.blocks as RunBlock[],
    events: data.events.slice(-100) as RunEvent[],
  };
}
export const isActiveRun = (state: RunState) =>
  state === "queued" || state === "running";
