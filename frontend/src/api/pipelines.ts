import { api, ApiError } from "./client";
import { isProjectId } from "./projects";
import type { Definition } from "../state/graph";

export interface PipelineSummary {
  id: string;
  project_id: string;
  name: string;
  revision: number;
}
export interface SavedPipeline extends PipelineSummary {
  definition: Definition;
}
export interface PipelinePage {
  items: PipelineSummary[];
  total: number;
  offset: number;
  limit: number;
}
function object(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function invalid(): never {
  throw new ApiError(
    "The API returned an unsupported pipeline response. Your draft has not been replaced.",
    "invalid-response",
  );
}
function summary(v: unknown, projectId: string): PipelineSummary {
  if (
    !object(v) ||
    typeof v.id !== "string" ||
    !isProjectId(v.id) ||
    v.project_id !== projectId ||
    typeof v.name !== "string" ||
    !v.name.trim() ||
    !Number.isSafeInteger(v.revision) ||
    Number(v.revision) < 1
  )
    return invalid();
  return {
    id: v.id,
    project_id: projectId,
    name: v.name,
    revision: Number(v.revision),
  };
}
export function parseDefinition(v: unknown): Definition {
  if (
    !object(v) ||
    v.schema_version !== 1 ||
    !Array.isArray(v.nodes) ||
    !Array.isArray(v.edges)
  )
    return invalid();
  const ids = new Set<string>();
  for (const n of v.nodes) {
    if (
      !object(n) ||
      typeof n.id !== "string" ||
      ids.has(n.id) ||
      typeof n.block_id !== "string" ||
      typeof n.block_version !== "string" ||
      !object(n.config)
    )
      return invalid();
    ids.add(n.id);
  }
  const edgeIds = new Set<string>();
  for (const e of v.edges) {
    if (
      !object(e) ||
      typeof e.id !== "string" ||
      edgeIds.has(e.id) ||
      !object(e.source) ||
      !object(e.target) ||
      typeof e.source.node_id !== "string" ||
      typeof e.target.node_id !== "string" ||
      !ids.has(e.source.node_id) ||
      !ids.has(e.target.node_id) ||
      typeof e.source.port !== "string" ||
      typeof e.target.port !== "string"
    )
      return invalid();
    edgeIds.add(e.id);
  }
  const layout = v.layout ?? { positions: {} };
  if (!object(layout) || !object(layout.positions)) return invalid();
  for (const [id, p] of Object.entries(layout.positions))
    if (
      !ids.has(id) ||
      !object(p) ||
      typeof p.x !== "number" ||
      !Number.isFinite(p.x) ||
      typeof p.y !== "number" ||
      !Number.isFinite(p.y)
    )
      return invalid();
  return structuredClone({ ...v, layout }) as unknown as Definition;
}
function saved(v: unknown, projectId: string, id?: string): SavedPipeline {
  const result = summary(v, projectId);
  if (!object(v) || (id && result.id !== id)) return invalid();
  return { ...result, definition: parseDefinition(v.definition) };
}
const path = (projectId: string) => {
  if (!isProjectId(projectId)) return invalid();
  return `/projects/${projectId}/pipelines`;
};
export async function listPipelines(
  projectId: string,
  offset: number,
  signal?: AbortSignal,
): Promise<PipelinePage> {
  const { data } = await api.get<unknown>(path(projectId), {
    params: { offset, limit: 20 },
    signal,
  });
  if (
    !object(data) ||
    !Array.isArray(data.items) ||
    data.offset !== offset ||
    data.limit !== 20 ||
    !Number.isSafeInteger(data.total) ||
    Number(data.total) < 0 ||
    data.items.length > 20
  )
    return invalid();
  return {
    items: data.items.map((v) => summary(v, projectId)),
    total: Number(data.total),
    offset,
    limit: 20,
  };
}
export async function openPipeline(
  projectId: string,
  id: string,
): Promise<SavedPipeline> {
  const { data } = await api.get<unknown>(
    `${path(projectId)}/${encodeURIComponent(id)}`,
  );
  return saved(data, projectId, id);
}
export async function savePipeline(
  projectId: string,
  name: string,
  definition: Definition,
  current?: { id: string; revision: number },
): Promise<SavedPipeline> {
  try {
    const { data } = current
      ? await api.put<unknown>(
          `${path(projectId)}/${encodeURIComponent(current.id)}`,
          { name, definition, expected_revision: current.revision },
        )
      : await api.post<unknown>(path(projectId), { name, definition });
    return saved(data, projectId, current?.id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 409)
      throw new ApiError(
        "The pipeline name is already used or a newer revision exists. Open the latest version, or choose another name and Save a copy. Your draft is retained.",
        "http",
        409,
      );
    if (error instanceof ApiError && error.status === 422)
      throw new ApiError(
        "The pipeline is invalid. Use schema version 1, an acyclic graph, a name up to 128 characters, and configuration without credentials or machine paths. Your draft is retained.",
        "http",
        422,
      );
    throw error;
  }
}
