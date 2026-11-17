// AI contribution: 50% or more AI-generated
import { api } from "./client";
import { invalidResponse, object } from "./guards";
import { isProjectId } from "./projects";

export interface ArtifactIdentity {
  artifactId: string;
  runId: string;
  revisionId: string;
}
export interface ArtifactPage {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  offset: number;
  limit: number;
  has_more: boolean;
}
export const ARTIFACT_PAGE_SIZE = 50;
const invalid = invalidResponse(
  "The API returned mismatched or invalid output rows.",
);
export async function queryArtifact(
  identity: ArtifactIdentity,
  offset: number,
  signal?: AbortSignal,
): Promise<ArtifactPage> {
  if (
    !Object.values(identity).every(isProjectId) ||
    !Number.isSafeInteger(offset) ||
    offset < 0
  )
    return invalid();
  const { data } = await api.post<unknown>(
    `/artifacts/${identity.artifactId}/query`,
    { columns: [], offset, limit: ARTIFACT_PAGE_SIZE },
    { signal },
  );
  if (
    !object(data) ||
    data.schema_version !== 1 ||
    data.artifact_id !== identity.artifactId ||
    data.run_id !== identity.runId ||
    data.pipeline_revision_id !== identity.revisionId ||
    data.offset !== offset ||
    data.limit !== ARTIFACT_PAGE_SIZE ||
    typeof data.has_more !== "boolean" ||
    !Array.isArray(data.columns) ||
    data.columns.length > 100 ||
    !data.columns.every((c) => typeof c === "string") ||
    new Set(data.columns).size !== data.columns.length ||
    !Array.isArray(data.rows) ||
    data.rows.length > ARTIFACT_PAGE_SIZE ||
    !data.rows.every(
      (row) =>
        Array.isArray(row) &&
        row.length === (data.columns as unknown[]).length &&
        row.every(
          (v) =>
            v === null ||
            typeof v === "string" ||
            typeof v === "boolean" ||
            (typeof v === "number" && Number.isFinite(v)),
        ),
    )
  )
    return invalid();
  return data as unknown as ArtifactPage;
}
