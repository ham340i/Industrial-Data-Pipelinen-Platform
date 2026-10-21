import { api, ApiError } from "./client";
import type { Definition } from "../state/graph";

export interface Diagnostic {
  code: string;
  message: string;
  node_id: string | null;
  edge_id: string | null;
  port: string | null;
  field: string | null;
}
export interface ValidationReport {
  valid: boolean;
  diagnostics: Diagnostic[];
}
export type SemanticDefinition = Omit<Definition, "layout">;

function object(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
const optional = (v: unknown) => v === null || typeof v === "string";
function invalid(): never {
  throw new ApiError(
    "The API returned an unsupported validation response. Your draft is unchanged.",
    "invalid-response",
  );
}
export function parseReport(v: unknown): ValidationReport {
  if (
    !object(v) ||
    typeof v.valid !== "boolean" ||
    !Array.isArray(v.diagnostics) ||
    v.valid !== (v.diagnostics.length === 0)
  )
    return invalid();
  const diagnostics = v.diagnostics.map((d: unknown): Diagnostic => {
    if (
      !object(d) ||
      typeof d.code !== "string" ||
      typeof d.message !== "string" ||
      !d.message.trim() ||
      !["node_id", "edge_id", "port", "field"].every((k) => optional(d[k]))
    )
      return invalid();
    return {
      code: d.code,
      message: d.message,
      node_id: (d.node_id as string | null) ?? null,
      edge_id: (d.edge_id as string | null) ?? null,
      port: (d.port as string | null) ?? null,
      field: (d.field as string | null) ?? null,
    };
  });
  return { valid: v.valid, diagnostics };
}
export async function validatePipeline(
  definition: SemanticDefinition,
  signal?: AbortSignal,
): Promise<ValidationReport> {
  try {
    const { data } = await api.post<unknown>(
      "/pipelines/validate",
      { definition },
      { signal },
    );
    return parseReport(data);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422)
      throw new ApiError(
        "The pipeline could not be checked because its definition is malformed. Your draft is unchanged.",
        "http",
        422,
      );
    throw error;
  }
}
