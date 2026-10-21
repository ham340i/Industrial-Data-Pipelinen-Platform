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
