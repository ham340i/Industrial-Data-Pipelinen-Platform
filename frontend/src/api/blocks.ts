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
export async function getBlocks(
  signal?: AbortSignal,
): Promise<BlockMetadata[]> {
  const { data } = await api.get<unknown>("/blocks", { signal });
  if (
    !Array.isArray(data) ||
    !data.every(
      (b: unknown) =>
        object(b) &&
        b.sdk_version === 1 &&
        ["block_id", "version", "name", "category"].every(
          (k) => typeof b[k] === "string" && b[k].trim(),
        ) &&
        (b.library_visible === undefined ||
          typeof b.library_visible === "boolean") &&
        (b.block_type === undefined ||
          ["trigger", "source", "transform", "quality", "sink"].includes(
            String(b.block_type),
          )) &&
        (b.supports_preview === undefined ||
          (typeof b.supports_preview === "boolean" &&
            (b.supports_preview
              ? b.preview_reason === null &&
                ["source", "transform"].includes(String(b.block_type))
              : typeof b.preview_reason === "string" &&
                !!b.preview_reason.trim()))) &&
        ports(b.inputs) &&
        ports(b.outputs) &&
        object(b.config_schema),
    )
  ) {
    throw new ApiError(
      "The API returned unsupported block metadata.",
      "invalid-response",
    );
  }
  return data as BlockMetadata[];
}
