import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { Edge } from "@xyflow/react";
import {
  validatePipeline,
  type Diagnostic,
  type SemanticDefinition,
  type ValidationReport,
} from "../api/validation";
import { serializeGraph, type BlockNode } from "./graph";

/** Positions and selection never affect validity, so they are not sent. */
export function semanticDefinition(
  nodes: BlockNode[],
  edges: Edge[],
): SemanticDefinition {
  const { schema_version, nodes: n, edges: e } = serializeGraph(nodes, edges);
  return { schema_version, nodes: n, edges: e };
}

export interface PlacedDiagnostics {
  /** Diagnostics about a node itself: configuration, inputs, availability. */
  byNode: Map<string, Diagnostic[]>;
  /** Diagnostics about a connection: cycles, ports, cardinality. */
  byEdge: Map<string, Diagnostic[]>;
  /** Pipeline-wide problems or references the canvas cannot show. */
  unplaced: Diagnostic[];
}
const push = (map: Map<string, Diagnostic[]>, key: string, d: Diagnostic) =>
  map.set(key, [...(map.get(key) ?? []), d]);

/**
 * Attach backend diagnostics to what the canvas displays. The backend owns the
 * rules; this only decides where each message appears, preserving its order.
 */
export function placeDiagnostics(
  diagnostics: Diagnostic[],
  nodes: { id: string }[],
  edges: { id: string }[],
): PlacedDiagnostics {
  const nodeIds = new Set(nodes.map((n) => n.id)),
    edgeIds = new Set(edges.map((e) => e.id));
  const placed: PlacedDiagnostics = {
    byNode: new Map(),
    byEdge: new Map(),
    unplaced: [],
  };
  for (const d of diagnostics) {
    if (d.edge_id !== null && edgeIds.has(d.edge_id))
      push(placed.byEdge, d.edge_id, d);
    else if (d.edge_id === null && d.node_id !== null && nodeIds.has(d.node_id))
      push(placed.byNode, d.node_id, d);
    else placed.unplaced.push(d);
  }
  return placed;
}

/** Display copies of edges with problems; the stored edges are not changed. */
export function markEdges(
  edges: Edge[],
  byEdge: Map<string, Diagnostic[]>,
  color: string,
): Edge[] {
  return edges.map((e) => {
    const problems = byEdge.get(e.id);
    if (!problems) return e;
    return {
      ...e,
      className: "invalid-connection",
      ariaLabel: `Connection problem: ${problems.map((p) => p.message).join(" ")}`,
      label: problems.length > 1 ? `${problems.length} problems` : "Problem",
      style: { stroke: color, strokeWidth: 2 },
      labelStyle: { fill: color, fontWeight: 600 },
    };
  });
}

/** Field messages for the configuration panel (#17) to show beside inputs. */
export function fieldMessages(
  diagnostics: Diagnostic[],
  nodeId: string,
): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const d of diagnostics)
    if (d.node_id === nodeId && d.field !== null)
      (result[d.field] ??= []).push(d.message);
  return result;
}

export interface ValidationState {
  report: ValidationReport | undefined;
  /** The report describes exactly the graph currently on the canvas. */
  current: boolean;
  error: Error | null;
  /** Execution stays disabled until the current graph is known to be valid. */
  canRun: boolean;
}

/**
 * Re-check the draft shortly after each semantic edit. Validation is read-only:
 * it never writes to the editor store, so showing problems keeps every edit.
 */
export function usePipelineValidation(
  nodes: BlockNode[],
  edges: Edge[],
  delay = 300,
): ValidationState {
  const key = useMemo(
    () => JSON.stringify(semanticDefinition(nodes, edges)),
    [nodes, edges],
  );
  const [checked, setChecked] = useState(key);
  useEffect(() => {
    const timer = setTimeout(() => setChecked(key), delay);
    return () => clearTimeout(timer);
  }, [key, delay]);
  const query = useQuery({
    queryKey: ["validation", checked],
    queryFn: ({ signal }) =>
      validatePipeline(JSON.parse(checked) as SemanticDefinition, signal),
    retry: false,
    staleTime: Infinity,
    placeholderData: keepPreviousData,
  });
  const current =
    checked === key && query.isSuccess && !query.isPlaceholderData;
  return {
    report: query.data,
    current,
    error: checked === key && query.isError ? query.error : null,
    canRun: current && query.data?.valid === true,
  };
}
