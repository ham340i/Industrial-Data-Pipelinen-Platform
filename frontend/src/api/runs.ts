// AI contribution: 50% or more AI-generated
import { object, invalidResponse } from "./guards";
import { api } from "./client";
import { isProjectId } from "./projects";

export interface RunDetail {
  id: string;
  project_id: string;
  pipeline_id: string;
  revision: number;
  state: string;
  duration_ms: number | null;
  row_count: number | null;
  error: { code: string; reason: string } | null;
  blocks: {
    node_id: string;
    state: string;
    duration_ms: number | null;
    rows_in: number | null;
    rows_out: number | null;
    error: { code: string; reason: string } | null;
  }[];
  events: { sequence: number; message: string }[];
  outputs: {
    id: string;
    name: string;
    artifact_ref: string;
    row_count: number | null;
  }[];
}
const count = (v: unknown) =>
  v === null || (Number.isSafeInteger(v) && Number(v) >= 0);
const failure = (v: unknown) =>
  v === null ||
  (object(v) && typeof v.code === "string" && typeof v.reason === "string");
const invalid = invalidResponse(
  "The API returned an unsupported run response.",
);
export function parseRun(
  v: unknown,
  projectId: string,
  pipelineId: string,
  runId: string,
): RunDetail {
  if (
    !object(v) ||
    v.schema_version !== 1 ||
    v.id !== runId ||
    v.project_id !== projectId ||
    v.pipeline_id !== pipelineId ||
    !Number.isSafeInteger(v.revision) ||
    Number(v.revision) < 1 ||
    !["queued", "running", "succeeded", "failed", "cancelled"].includes(
      String(v.state),
    ) ||
    !count(v.duration_ms) ||
    !count(v.row_count) ||
    !failure(v.error) ||
    !Array.isArray(v.blocks) ||
    !Array.isArray(v.events) ||
    !Array.isArray(v.outputs)
  )
    return invalid();
  for (const b of v.blocks)
    if (
      !object(b) ||
      typeof b.node_id !== "string" ||
      !["queued", "running", "completed", "failed", "skipped"].includes(
        String(b.state),
      ) ||
      !count(b.duration_ms) ||
      !count(b.rows_in) ||
      !count(b.rows_out) ||
      !failure(b.error)
    )
      return invalid();
  for (const e of v.events)
    if (
      !object(e) ||
      !Number.isSafeInteger(e.sequence) ||
      typeof e.message !== "string"
    )
      return invalid();
  for (const o of v.outputs)
    if (
      !object(o) ||
      typeof o.id !== "string" ||
      typeof o.name !== "string" ||
      typeof o.artifact_ref !== "string" ||
      !count(o.row_count)
    )
      return invalid();
  return v as unknown as RunDetail;
}
export async function executePipeline(
  projectId: string,
  pipelineId: string,
): Promise<string> {
  if (!isProjectId(projectId) || !isProjectId(pipelineId)) return invalid();
  const { data } = await api.post<unknown>(
    `/projects/${projectId}/pipelines/${pipelineId}/execute`,
  );
  if (
    !object(data) ||
    typeof data.run_id !== "string" ||
    !isProjectId(data.run_id) ||
    !["queued", "running", "succeeded", "failed", "cancelled"].includes(
      String(data.state),
    )
  )
    return invalid();
  return data.run_id;
}
export async function getRun(
  projectId: string,
  pipelineId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<RunDetail> {
  if (![projectId, pipelineId, runId].every(isProjectId)) return invalid();
  const { data } = await api.get<unknown>(`/runs/${runId}`, { signal });
  return parseRun(data, projectId, pipelineId, runId);
}
