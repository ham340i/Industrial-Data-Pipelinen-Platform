import { beforeEach, expect, it } from "vitest";
import { useEditorStore } from "./editor";
import { compatible, serializeGraph } from "./graph";
import { sampleBlock, tablePort } from "../test/blocks";

beforeEach(() => useEditorStore.getState().reset());
function threeNodes() {
  for (let i = 0; i < 3; i++) useEditorStore.getState().addBlock(sampleBlock);
  return useEditorStore.getState().nodes.map((n) => n.id);
}
const connect = (source: string, target: string) =>
  useEditorStore
    .getState()
    .connect({ source, target, sourceHandle: "table", targetHandle: "table" }, [
      sampleBlock,
    ]);
it("preserves stable IDs, config and positions in portable JSON without React Flow internals", () => {
  const [a, b] = threeNodes();
  connect(a, b);
  useEditorStore
    .getState()
    .changeNodes([{ type: "position", id: a, position: { x: 123, y: -45 } }]);
  const s = useEditorStore.getState(),
    graph = serializeGraph(s.nodes, s.edges);
  expect(graph.nodes[0]).toEqual({
    id: a,
    block_id: sampleBlock.block_id,
    block_version: "1.0.0",
    config: { amount: 1 },
  });
  expect(graph.layout.positions[a]).toEqual({ x: 123, y: -45 });
  expect(graph.edges[0].source).toEqual({ node_id: a, port: "table" });
  graph.nodes[0].config.amount = 99;
  expect(s.nodes[0].data.config.amount).toBe(1);
});
it("rejects duplicate, self, cycle and occupied-input connections without erasing edits", () => {
  const [a, b, c] = threeNodes();
  connect(a, b);
  for (const [source, target] of [
    [a, b],
    [a, a],
    [b, a],
    [c, b],
  ]) {
    connect(source, target);
    expect(useEditorStore.getState().error).toBeTruthy();
    expect(useEditorStore.getState().edges).toHaveLength(1);
    expect(useEditorStore.getState().nodes).toHaveLength(3);
  }
});
it("removes incident edges when deleting a node and clears selection", () => {
  const [a, b] = threeNodes();
  connect(a, b);
  useEditorStore.getState().selectNode(a);
  useEditorStore.getState().deleteSelected();
  expect(useEditorStore.getState().edges).toHaveLength(0);
  expect(useEditorStore.getState().selectedNodeId).toBeNull();
  expect(useEditorStore.getState().nodes).toHaveLength(2);
});
it("matches SDK types, nullability, open schemas, control and cardinality", () => {
  expect(compatible(tablePort, tablePort)).toBe(true);
  expect(compatible({ ...tablePort, many: true }, tablePort)).toBe(false);
  expect(
    compatible({ ...tablePort, kind: "control", data_schema: null }, tablePort),
  ).toBe(false);
  expect(
    compatible(
      {
        ...tablePort,
        data_schema: {
          columns: [{ name: "value", dtype: "integer", nullable: true }],
          allow_extra_columns: false,
        },
      },
      tablePort,
    ),
  ).toBe(false);
  expect(
    compatible(
      {
        ...tablePort,
        data_schema: {
          columns: [{ name: "value", dtype: "string", nullable: false }],
          allow_extra_columns: false,
        },
      },
      tablePort,
    ),
  ).toBe(false);
  expect(
    compatible(
      {
        ...tablePort,
        data_schema: { ...tablePort.data_schema!, allow_extra_columns: true },
      },
      tablePort,
    ),
  ).toBe(false);
});
