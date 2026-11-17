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
const cellValid = (v: unknown) =>
  v === null ||
  typeof v === "string" ||
  typeof v === "boolean" ||
  (typeof v === "number" && Number.isFinite(v));

function columnsValid(columns: unknown): columns is string[] {
  return (
    Array.isArray(columns) &&
    columns.length <= 100 &&
    columns.every((c) => typeof c === "string") &&
    new Set(columns).size === columns.length
  );
}
function rowsValid(rows: unknown, width: number): boolean {
  return (
    Array.isArray(rows) &&
    rows.length <= ARTIFACT_PAGE_SIZE &&
    rows.every(
      (row) =>
        Array.isArray(row) && row.length === width && row.every(cellValid),
    )
  );
}
/** The page must echo the requested artifact, run, revision and window. */
function validPage(
  data: unknown,
  identity: ArtifactIdentity,
  offset: number,
): boolean {
  if (!object(data) || !columnsValid(data.columns)) return false;
  return [
    data.schema_version === 1,
    data.artifact_id === identity.artifactId,
    data.run_id === identity.runId,
    data.pipeline_revision_id === identity.revisionId,
    data.offset === offset,
    data.limit === ARTIFACT_PAGE_SIZE,
    typeof data.has_more === "boolean",
    rowsValid(data.rows, data.columns.length),
  ].every(Boolean);
}
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
  if (!validPage(data, identity, offset)) return invalid();
  return data as unknown as ArtifactPage;
}
