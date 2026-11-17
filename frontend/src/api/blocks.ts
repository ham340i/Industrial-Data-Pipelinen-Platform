// AI contribution: 50% or more AI-generated
import { api, ApiError } from "./client";

export interface Column {
  name: string;
  dtype: "string" | "integer" | "number" | "boolean";
  nullable: boolean;
}
export interface Port {
  name: string;
  kind: "data" | "control";
  required: boolean;
  many: boolean;
  data_schema: { columns: Column[]; allow_extra_columns: boolean } | null;
}
export interface BlockMetadata {
  sdk_version: number;
  block_id: string;
  version: string;
  name: string;
  category: string;
  // Older catalogs omit this field; omission preserves their visible default.
  library_visible?: boolean;
  block_type?: "trigger" | "source" | "transform" | "quality" | "sink";
  supports_preview?: boolean;
  preview_reason?: string | null;
  inputs: Port[];
  outputs: Port[];
  config_schema: Record<string, unknown>;
}
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function ports(value: unknown): value is Port[] {
  return (
    Array.isArray(value) &&
    value.every((p: unknown) => {
      if (
        !object(p) ||
        typeof p.name !== "string" ||
        !p.name.trim() ||
        typeof p.required !== "boolean" ||
        typeof p.many !== "boolean"
      )
        return false;
      if (p.kind === "control") return p.data_schema === null;
      if (p.kind !== "data" || !object(p.data_schema)) return false;
      const s = p.data_schema;
      return (
        typeof s.allow_extra_columns === "boolean" &&
        Array.isArray(s.columns) &&
        s.columns.every(
          (c: unknown) =>
            object(c) &&
            typeof c.name === "string" &&
            ["string", "integer", "number", "boolean"].includes(
              String(c.dtype),
            ) &&
            typeof c.nullable === "boolean",
        )
      );
    }) &&
    new Set(value.map((p: Port) => p.name)).size === value.length
  );
}
const BLOCK_TYPES = ["trigger", "source", "transform", "quality", "sink"];
const optionalBoolean = (v: unknown) =>
  v === undefined || typeof v === "boolean";

/** A previewable block has no reason; any other block must explain why. */
function previewFieldsValid(b: Record<string, unknown>): boolean {
  if (b.supports_preview === undefined) return true;
  if (typeof b.supports_preview !== "boolean") return false;
  if (b.supports_preview)
    return (
      b.preview_reason === null &&
      ["source", "transform"].includes(String(b.block_type))
    );
  return typeof b.preview_reason === "string" && !!b.preview_reason.trim();
}
function validBlock(b: unknown): boolean {
  if (!object(b)) return false;
  return [
    b.sdk_version === 1,
    ["block_id", "version", "name", "category"].every(
      (k) => typeof b[k] === "string" && !!b[k].trim(),
    ),
    optionalBoolean(b.library_visible),
    b.block_type === undefined || BLOCK_TYPES.includes(String(b.block_type)),
    previewFieldsValid(b),
    ports(b.inputs),
    ports(b.outputs),
    object(b.config_schema),
  ].every(Boolean);
}
export async function getBlocks(
  signal?: AbortSignal,
): Promise<BlockMetadata[]> {
  const { data } = await api.get<unknown>("/blocks", { signal });
  if (!Array.isArray(data) || !data.every(validBlock)) {
    throw new ApiError(
      "The API returned unsupported block metadata.",
      "invalid-response",
    );
  }
  return data as BlockMetadata[];
}
