import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  parseReport,
  validatePipeline,
  type Diagnostic,
} from "../api/validation";
import { server } from "../test/server";
import { sampleBlock } from "../test/blocks";
import { useEditorStore } from "./editor";
import {
  fieldMessages,
  markEdges,
  placeDiagnostics,
  semanticDefinition,
} from "./validation";

const url = "http://127.0.0.1:8000/api/v1/pipelines/validate";
const diagnostic = (d: Partial<Diagnostic>): Diagnostic => ({
  code: "missing_input",
  message: "Fix it.",
  node_id: null,
  edge_id: null,
  port: null,
  field: null,
  ...d,
});

describe("diagnostic placement", () => {
  const nodes = [{ id: "a" }, { id: "b" }];
  const edges = [{ id: "ab" }];
  // Representative backend output for an invalid graph, in backend order.
  const report = [
    diagnostic({ code: "empty_pipeline" }),
    diagnostic({ code: "dangling_edge", edge_id: "deleted-edge" }),
    diagnostic({ code: "cycle", node_id: "a", edge_id: "ab" }),
    diagnostic({ code: "invalid_config", node_id: "a", field: "amount" }),
    diagnostic({ code: "unknown_config", node_id: "a", field: "colour" }),
    diagnostic({
      code: "incompatible_ports",
      node_id: "b",
      edge_id: "ab",
      port: "table",
    }),
    diagnostic({ code: "missing_input", node_id: "b", port: "table" }),
    diagnostic({ code: "duplicate_node", node_id: "ghost" }),
  ];

  it("puts node, connection and field problems where the canvas shows them", () => {
    const placed = placeDiagnostics(report, nodes, edges);
    expect(placed.byEdge.get("ab")?.map((d) => d.code)).toEqual([
      "cycle",
      "incompatible_ports",
    ]);
    expect(placed.byNode.get("a")?.map((d) => d.field)).toEqual([
      "amount",
      "colour",
    ]);
    expect(placed.byNode.get("b")?.map((d) => d.code)).toEqual([
      "missing_input",
    ]);
    expect(placed.unplaced.map((d) => d.code)).toEqual([
      "empty_pipeline",
      "dangling_edge",
      "duplicate_node",
    ]);
  });

  it("is deterministic and loses no diagnostic", () => {
    const first = placeDiagnostics(report, nodes, edges);
    const second = placeDiagnostics(report, [...nodes].reverse(), edges);
    expect(second).toEqual(first);
    const count =
      first.unplaced.length +
      [...first.byNode.values(), ...first.byEdge.values()].flat().length;
    expect(count).toBe(report.length);
  });

  it("exposes field messages for the configuration panel", () => {
    expect(fieldMessages(report, "a")).toEqual({
      amount: ["Fix it."],
      colour: ["Fix it."],
    });
    expect(fieldMessages(report, "b")).toEqual({});
  });

  it("marks problem connections on display copies only", () => {
    const stored = [
      { id: "ab", source: "a", target: "b" },
      { id: "bc", source: "b", target: "c" },
    ];
    const snapshot = structuredClone(stored);
    const placed = placeDiagnostics(report, nodes, stored);
    const shown = markEdges(stored, placed.byEdge, "red");
    expect(shown[0]).toMatchObject({
      id: "ab",
      className: "invalid-connection",
      label: "2 problems",
      style: { stroke: "red" },
    });
    expect(shown[0].ariaLabel).toContain("Fix it.");
    expect(shown[1]).toBe(stored[1]);
    expect(stored).toEqual(snapshot);
  });
});

describe("validation API", () => {
  it("sends the semantic graph without layout", async () => {
    useEditorStore.getState().addBlock(sampleBlock, { x: 5, y: 6 });
    const { nodes, edges } = useEditorStore.getState();
    let body: unknown;
    server.use(
      http.post(url, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ valid: true, diagnostics: [] });
      }),
    );
    const definition = semanticDefinition(nodes, edges);
    expect(definition).not.toHaveProperty("layout");
    await expect(validatePipeline(definition)).resolves.toEqual({
      valid: true,
      diagnostics: [],
    });
    expect(body).toEqual({
      definition: {
        schema_version: 1,
        nodes: [
          {
            id: nodes[0].id,
            block_id: sampleBlock.block_id,
            block_version: "1.0.0",
            config: { amount: 1 },
          },
        ],
        edges: [],
      },
    });
  });

  it("explains malformed requests without blaming the draft", async () => {
    server.use(
      http.post(url, () =>
        HttpResponse.json(
          { error: { code: "validation_error" } },
          { status: 422 },
        ),
      ),
    );
    await expect(
      validatePipeline({ schema_version: 1, nodes: [], edges: [] }),
    ).rejects.toThrow("Your draft is unchanged.");
  });

  it.each([
    null,
    { valid: true },
    { valid: true, diagnostics: [diagnostic({})] },
    { valid: false, diagnostics: [] },
    { valid: false, diagnostics: [{ ...diagnostic({}), message: " " }] },
    { valid: false, diagnostics: [{ ...diagnostic({}), node_id: 3 }] },
  ])("rejects unsupported responses %#", (value) => {
    expect(() => parseReport(value)).toThrow("unsupported validation response");
  });
});
