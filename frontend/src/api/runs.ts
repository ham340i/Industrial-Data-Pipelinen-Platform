// AI contribution: 50% or more AI-generated
import { api, ApiError } from "./client";
import { object, invalidResponse } from "./guards";
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
  outputs: {
    id: string;
    name: string;
    artifact_ref: string;
    row_count: number | null;
  }[];
}
const states = ["queued", "running", "succeeded", "failed", "cancelled"];
const count = (v: unknown): v is number =>
  Number.isSafeInteger(v) && Number(v) >= 0;
const measurement = (v: unknown) => v === null || count(v);
const date = (v: unknown) =>
  typeof v === "string" && Number.isFinite(Date.parse(v));
const optionalDate = (v: unknown) => v === null || date(v);
const failure = (v: unknown) =>
  v === null ||
  (object(v) && typeof v.code === "string" && typeof v.reason === "string");
const invalid = invalidResponse(
  "The API returned unsupported or mismatched run evidence. Refresh to try again.",
);
const uuid = (v: unknown) => typeof v === "string" && isProjectId(v);
const nullableText = (v: unknown) => v === null || typeof v === "string";
const blockStates = ["queued", "running", "completed", "failed", "skipped"];
const eventLevels = ["info", "warning", "error"];

function summary(
  v: unknown,
  projectId: string,
  pipelineId: string,
): RunSummary {
  if (!object(v)) return invalid();
  const checks = [
    v.schema_version === 1,
    uuid(v.id),
    v.project_id === projectId,
    v.pipeline_id === pipelineId,
    uuid(v.pipeline_revision_id),
    count(v.revision) && v.revision >= 1,
    states.includes(String(v.state)),
    date(v.created_at),
    optionalDate(v.started_at),
    optionalDate(v.ended_at),
    measurement(v.duration_ms),
    measurement(v.row_count),
    failure(v.error),
  ];
  if (!checks.every(Boolean)) return invalid();
  return v as unknown as RunSummary;
}
function validBlock(
  b: unknown,
  ids: Set<string>,
): b is Record<string, unknown> & { node_id: string } {
  if (!object(b)) return false;
  return [
    typeof b.node_id === "string" && !ids.has(b.node_id),
    typeof b.block_id === "string",
    typeof b.block_version === "string",
    count(b.position),
    blockStates.includes(String(b.state)),
    optionalDate(b.started_at),
    optionalDate(b.ended_at),
    measurement(b.duration_ms),
    measurement(b.rows_in),
    measurement(b.rows_out),
    failure(b.error),
  ].every(Boolean);
}
function validEvent(
  e: unknown,
  previous: number,
): e is Record<string, unknown> & { sequence: number } {
  if (!object(e)) return false;
  return [
    count(e.sequence) && e.sequence > previous,
    date(e.created_at),
    eventLevels.includes(String(e.level)),
    nullableText(e.node_id),
    typeof e.kind === "string",
    nullableText(e.code),
    typeof e.message === "string",
  ].every(Boolean);
}
function validOutput(o: unknown): boolean {
  return (
    object(o) &&
    typeof o.id === "string" &&
    typeof o.name === "string" &&
    typeof o.artifact_ref === "string" &&
    measurement(o.row_count)
  );
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
export function parseRun(
  data: unknown,
  projectId: string,
  pipelineId: string,
  runId: string,
): RunDetail {
  const result = summary(data, projectId, pipelineId);
  if (
    !object(data) ||
    result.id !== runId ||
    !Array.isArray(data.blocks) ||
    !Array.isArray(data.events) ||
    !Array.isArray(data.outputs)
  )
    return invalid();
  const ids = new Set<string>();
  for (const b of data.blocks) {
    if (!validBlock(b, ids)) return invalid();
    ids.add(b.node_id);
  }
  let previous = -1;
  for (const e of data.events) {
    if (!validEvent(e, previous)) return invalid();
    previous = e.sequence;
  }
  if (!data.outputs.every((o) => validOutput(o))) return invalid();
  return {
    ...result,
    blocks: data.blocks as RunBlock[],
    events: data.events.slice(-100) as RunEvent[],
    outputs: data.outputs as RunDetail["outputs"],
  };
}

/** A refused execution is distinct from an uncertain transport failure. */
export class ExecutionRequestError extends ApiError {
  constructor(
    message: string,
    status: number,
    public readonly nodeId: string | null = null,
  ) {
    super(message, "http", status);
  }
}

export const isActiveRun = (state: RunState) =>
  state === "queued" || state === "running";

const runStates = ["queued", "running", "succeeded", "failed", "cancelled"];

function checkExecuteRequest(
  projectId: string,
  pipelineId: string,
  expectedRevision?: number,
): void {
  const revisionValid =
    expectedRevision === undefined ||
    (Number.isSafeInteger(expectedRevision) && expectedRevision >= 1);
  if (!isProjectId(projectId) || !isProjectId(pipelineId) || !revisionValid)
    invalid();
}
function failedNode(error: Record<string, unknown> | null): string | null {
  const context = error?.node_context;
  return typeof context === "string" &&
    context.length > 0 &&
    context.length <= 128
    ? context
    : null;
}
/** Translate a refused or failed execute request into a public error. */
function executionFailure(status: number, data: unknown): never {
  const error = object(data) && object(data.error) ? data.error : null;
  if (status === 409 && error?.code === "revision_conflict")
    throw new ExecutionRequestError(
      "This pipeline changed since it was opened. Open the latest version or save a copy before running.",
      status,
    );
  if (status === 422)
    throw new ExecutionRequestError(
      "The saved pipeline could not run. Check its configuration and validation problems.",
      status,
      failedNode(error),
    );
  if (status < 500)
    throw new ExecutionRequestError(
      `The API rejected the execution request (HTTP ${status}).`,
      status,
    );
  // An unexpected server failure can happen after a run has been recorded.
  throw new ApiError(
    `The execution request failed (HTTP ${status}).`,
    "http",
    status,
  );
}
function acceptedRunId(status: number, data: unknown): string {
  if (
    status < 200 ||
    status >= 300 ||
    !object(data) ||
    !uuid(data.run_id) ||
    !runStates.includes(String(data.state))
  )
    return invalid();
  return data.run_id as string;
}
export async function executePipeline(
  projectId: string,
  pipelineId: string,
  expectedRevision?: number,
): Promise<string> {
  checkExecuteRequest(projectId, pipelineId, expectedRevision);
  const { data, status } = await api.post<unknown>(
    `/projects/${projectId}/pipelines/${pipelineId}/execute`,
    expectedRevision === undefined
      ? undefined
      : { expected_revision: expectedRevision },
    { validateStatus: () => true },
  );
  if (status >= 400) executionFailure(status, data);
  return acceptedRunId(status, data);
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
