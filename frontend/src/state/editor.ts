import { create } from "zustand";
import {
  applyNodeChanges,
  applyEdgeChanges,
  type NodeChange,
  type EdgeChange,
  type Edge,
  type Connection,
} from "@xyflow/react";
import type { BlockMetadata } from "../api/blocks";
import type { SavedPipeline } from "../api/pipelines";
import { connectionError, serializeGraph, type BlockNode } from "./graph";

interface EditorState {
  pipelineId: string | null;
  revision: number | null;
  savedFingerprint: string | null;
  generation: number;
  busy: boolean;
  setBusy: (busy: boolean) => void;
  loadSaved: (pipeline: SavedPipeline) => void;
  draftName: string;
  selectedNodeId: string | null;
  projectId: string | null;
  nodes: BlockNode[];
  edges: Edge[];
  error: string | null;
  setProject: (id: string | null) => void;
  setDraftName: (name: string) => void;
  selectNode: (id: string | null) => void;
  addBlock: (block: BlockMetadata, position?: { x: number; y: number }) => void;
  changeNodes: (changes: NodeChange<BlockNode>[]) => void;
  changeEdges: (changes: EdgeChange[]) => void;
  connect: (connection: Connection, blocks: BlockMetadata[]) => void;
  deleteSelected: () => void;
  clearDraft: () => void;
  reset: () => void;
}
export function fingerprint(
  name: string,
  nodes: BlockNode[],
  edges: Edge[],
): string {
  return JSON.stringify({ name, definition: serializeGraph(nodes, edges) });
}
const initialState = {
  pipelineId: null,
  revision: null,
  savedFingerprint: null,
  generation: 0,
  busy: false,
  draftName: "",
  selectedNodeId: null,
  projectId: null,
  nodes: [] as BlockNode[],
  edges: [] as Edge[],
  error: null,
};

export const useEditorStore = create<EditorState>((set) => ({
  ...initialState,
  setBusy: (busy) => set({ busy }),
  loadSaved: (pipeline) =>
    set((state) => {
      const nodes: BlockNode[] = pipeline.definition.nodes.map((n, index) => ({
        id: n.id,
        type: "block",
        data: {
          block_id: n.block_id,
          block_version: n.block_version,
          config: structuredClone(n.config),
        },
        position: pipeline.definition.layout.positions[n.id] ?? {
          x: 60 + index * 40,
          y: 60 + index * 60,
        },
      }));
      const edges: Edge[] = pipeline.definition.edges.map((e) => ({
        id: e.id,
        source: e.source.node_id,
        sourceHandle: e.source.port,
        target: e.target.node_id,
        targetHandle: e.target.port,
      }));
      return {
        nodes,
        edges,
        draftName: pipeline.name,
        pipelineId: pipeline.id,
        revision: pipeline.revision,
        selectedNodeId: null,
        error: null,
        savedFingerprint: fingerprint(pipeline.name, nodes, edges),
        generation: state.generation + 1,
      };
    }),
  setProject: (projectId) =>
    set((state) =>
      state.projectId === projectId
        ? state
        : { ...initialState, projectId, generation: state.generation + 1 },
    ),
  setDraftName: (draftName) =>
    set((state) => (state.busy ? state : { draftName })),
  selectNode: (selectedNodeId) =>
    set((state) => ({
      selectedNodeId,
      nodes: state.nodes.map((n) => ({
        ...n,
        selected: n.id === selectedNodeId,
      })),
    })),
  addBlock: (block, position) =>
    set((state) => {
      if (state.busy) return state;
      const id = crypto.randomUUID();
      const properties = block.config_schema.properties as
        Record<string, { default?: unknown }> | undefined;
      const config = Object.fromEntries(
        Object.entries(properties ?? {})
          .filter(([, p]) => Object.hasOwn(p, "default"))
          .map(([k, p]) => [k, structuredClone(p.default)]),
      );
      return {
        nodes: [
          ...state.nodes.map((n) => ({ ...n, selected: false })),
          {
            id,
            type: "block",
            position: position ?? {
              x: 60 + state.nodes.length * 40,
              y: 60 + state.nodes.length * 60,
            },
            selected: true,
            data: {
              block_id: block.block_id,
              block_version: block.version,
              config,
            },
          },
        ],
        selectedNodeId: id,
        error: null,
      };
    }),
  changeNodes: (changes) =>
    set((state) => {
      if (state.busy) return state;
      const nodes = applyNodeChanges(changes, state.nodes);
      return {
        nodes,
        edges: state.edges.filter(
          (e) =>
            nodes.some((n) => n.id === e.source) &&
            nodes.some((n) => n.id === e.target),
        ),
        selectedNodeId: nodes.find((n) => n.selected)?.id ?? null,
      };
    }),
  changeEdges: (changes) =>
    set((state) =>
      state.busy ? state : { edges: applyEdgeChanges(changes, state.edges) },
    ),
  connect: (connection, blocks) =>
    set((state) => {
      if (state.busy) return state;
      const error = connectionError(
        connection,
        state.nodes,
        state.edges,
        blocks,
      );
      return error
        ? { error }
        : {
            error: null,
            edges: [...state.edges, { ...connection, id: crypto.randomUUID() }],
          };
    }),
  deleteSelected: () =>
    set((state) =>
      state.busy
        ? state
        : {
            nodes: state.nodes.filter((n) => n.id !== state.selectedNodeId),
            edges: state.edges.filter(
              (e) =>
                e.source !== state.selectedNodeId &&
                e.target !== state.selectedNodeId &&
                !e.selected,
            ),
            selectedNodeId: null,
          },
    ),
  clearDraft: () =>
    set((state) =>
      state.busy
        ? state
        : {
            ...initialState,
            projectId: state.projectId,
            generation: state.generation + 1,
          },
    ),
  reset: () =>
    set((state) => ({ ...initialState, generation: state.generation + 1 })),
}));
