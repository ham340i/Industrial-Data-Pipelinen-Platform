import type { Connection, Edge, Node } from "@xyflow/react";
import type { BlockMetadata, Port } from "../api/blocks";

export type BlockNode = Node<
  {
    block_id: string;
    block_version: string;
    config: Record<string, unknown>;
  },
  "block"
>;
export interface Definition {
  schema_version: 1;
  nodes: {
    id: string;
    block_id: string;
    block_version: string;
    config: Record<string, unknown>;
  }[];
  edges: {
    id: string;
    source: { node_id: string; port: string };
    target: { node_id: string; port: string };
  }[];
  layout: { positions: Record<string, { x: number; y: number }> };
}
export function serializeGraph(nodes: BlockNode[], edges: Edge[]): Definition {
  return JSON.parse(
    JSON.stringify({
      schema_version: 1,
      nodes: nodes.map(({ id, data }) => ({ id, ...data })),
      edges: edges.map((e) => ({
        id: e.id,
        source: { node_id: e.source, port: e.sourceHandle },
        target: { node_id: e.target, port: e.targetHandle },
      })),
      layout: {
        positions: Object.fromEntries(nodes.map((n) => [n.id, n.position])),
      },
    }),
  ) as Definition;
}
export function compatible(out: Port, input: Port): boolean {
  if (out.kind !== input.kind || (out.many && !input.many)) return false;
  if (out.kind === "control") return true;
  const a = out.data_schema,
    b = input.data_schema;
  if (!a || !b || (a.allow_extra_columns && !b.allow_extra_columns))
    return false;
  if (!b.allow_extra_columns && a.columns.length !== b.columns.length)
    return false;
  return b.columns.every((c) =>
    a.columns.some(
      (p) =>
        p.name === c.name && p.dtype === c.dtype && (c.nullable || !p.nullable),
    ),
  );
}
export function connectionError(
  c: Connection,
  nodes: BlockNode[],
  edges: Edge[],
  blocks: BlockMetadata[],
): string | null {
  const source = nodes.find((n) => n.id === c.source),
    target = nodes.find((n) => n.id === c.target);
  const metadata = (n: BlockNode) =>
    blocks.find(
      (b) =>
        b.block_id === n.data.block_id && b.version === n.data.block_version,
    );
  if (!source || !target) return "Choose existing nodes.";
  if (source.id === target.id) return "A node cannot connect to itself.";
  const out = metadata(source)?.outputs.find((p) => p.name === c.sourceHandle);
  const input = metadata(target)?.inputs.find((p) => p.name === c.targetHandle);
  if (!out || !input || !compatible(out, input))
    return "These ports have incompatible contracts.";
  if (
    edges.some(
      (e) =>
        e.source === c.source &&
        e.target === c.target &&
        e.sourceHandle === c.sourceHandle &&
        e.targetHandle === c.targetHandle,
    )
  )
    return "This connection already exists.";
  if (
    !input.many &&
    edges.some(
      (e) => e.target === c.target && e.targetHandle === c.targetHandle,
    )
  )
    return "This input accepts only one connection.";
  const pending = [target.id],
    seen = new Set<string>();
  while (pending.length) {
    const id = pending.pop()!;
    if (id === source.id) return "This connection would create a cycle.";
    if (seen.has(id)) continue;
    seen.add(id);
    pending.push(...edges.filter((e) => e.source === id).map((e) => e.target));
  }
  return null;
}
