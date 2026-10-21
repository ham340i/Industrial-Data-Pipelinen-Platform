import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { server } from "../test/server";
import { sampleBlock } from "../test/blocks";
import { useEditorStore } from "../state/editor";
import { serializeGraph } from "../state/graph";
import { ConfigurationPanel } from "./ConfigurationPanel";
import type { Diagnostic } from "../api/validation";
import sdk from "./sdk-example.json";

const url = "http://127.0.0.1:8000/api/v1/blocks";
const blocks = (schema: Record<string, unknown> = sdk.config_schema) => [
  { ...sampleBlock, config_schema: schema },
];
function seed(config: Record<string, unknown> = { amount: 1 }) {
  useEditorStore.setState({
    nodes: ["first", "second"].map((id) => ({
      id,
      type: "block",
      position: { x: 0, y: 0 },
      data: {
        block_id: sampleBlock.block_id,
        block_version: sampleBlock.version,
        config: structuredClone(config),
      },
    })),
    selectedNodeId: "first",
  });
}
function mount(diagnostics: Diagnostic[] = []) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <button onClick={() => useEditorStore.getState().selectNode("first")}>
        First
      </button>
      <button onClick={() => useEditorStore.getState().selectNode("second")}>
        Second
      </button>
      <ConfigurationPanel diagnostics={diagnostics} />
    </QueryClientProvider>,
  );
}
const amount = () => screen.getByRole("spinbutton", { name: "Amount" });
function ready() {
  server.use(http.get(url, () => HttpResponse.json(blocks())));
}

it("edits real graph configs, preserves selection values, and round-trips the saved definition", async () => {
  ready();
  seed();
  mount();
  const user = userEvent.setup();
  await screen.findByRole("spinbutton", { name: "Amount" });
  await user.clear(amount());
  await user.type(amount(), "42");
  await user.click(screen.getByRole("button", { name: "Second" }));
  expect(amount()).toHaveValue(1);
  await user.clear(amount());
  await user.type(amount(), "7");
  await user.click(screen.getByRole("button", { name: "First" }));
  expect(amount()).toHaveValue(42);
  const state = useEditorStore.getState();
  const definition = JSON.parse(
    JSON.stringify(serializeGraph(state.nodes, state.edges)),
  );
  expect(definition.nodes.map((n: { config: unknown }) => n.config)).toEqual([
    { amount: 42 },
    { amount: 7 },
  ]);
  act(() => {
    state.clearDraft();
    state.loadSaved({
      id: "saved",
      project_id: "p",
      name: "Roundtrip",
      revision: 1,
      definition,
    });
    state.selectNode("second");
  });
  expect(amount()).toHaveValue(7);
});

it("identifies required, range and type problems without overwriting invalid input", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json(
        blocks({
          type: "object",
          additionalProperties: false,
          required: ["amount"],
          properties: {
            amount: {
              type: "integer",
              title: "Amount",
              minimum: -1000,
              maximum: 1000,
            },
          },
        }),
      ),
    ),
  );
  seed({});
  mount();
  const user = userEvent.setup();
  await screen.findByText("This field is required.");
  expect(screen.getByRole("status")).toHaveTextContent("block first");
  await user.type(amount(), "1001");
  expect(screen.getByText("Use a value of at most 1000.")).toBeVisible();
  await user.clear(amount());
  await user.type(amount(), "1.5");
  expect(screen.getByText("Enter a valid integer.")).toBeVisible();
  await user.clear(amount());
  await user.type(amount(), "-1000");
  expect(amount()).toHaveValue(-1000);
  expect(amount()).not.toHaveAttribute("aria-invalid", "true");
});

it("shows only this node's backend field diagnostics and focuses the requested field", async () => {
  ready();
  seed();
  mount([
    {
      code: "invalid_config",
      message: "Server field constraint.",
      node_id: "first",
      edge_id: null,
      port: null,
      field: "amount",
    },
    {
      code: "invalid_config",
      message: "Other node problem.",
      node_id: "second",
      edge_id: null,
      port: null,
      field: "amount",
    },
  ]);
  await screen.findByRole("spinbutton", { name: "Amount" });
  expect(screen.getByText("Server field constraint.")).toBeVisible();
  expect(screen.queryByText("Other node problem.")).not.toBeInTheDocument();
  act(() => useEditorStore.getState().focusConfiguration("first", "amount"));
  expect(amount()).toHaveFocus();
});

it("retains configuration while registry metadata is loading", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get(url, async () => {
      await gate;
      return HttpResponse.json(blocks());
    }),
  );
  seed({ amount: 42 });
  mount();
  await screen.findByText(/Loading block definitions/);
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    amount: 42,
  });
  release();
  expect(await screen.findByRole("spinbutton", { name: "Amount" })).toHaveValue(
    42,
  );
});

it("recovers a registry failure through retry without reflecting the raw response", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json(
        { message: "fictional-private-value" },
        { status: 503 },
      ),
    ),
  );
  seed({ amount: 42 });
  mount();
  const user = userEvent.setup();
  await screen.findByText(/Block definitions could not be loaded/);
  expect(screen.queryByText(/fictional-private-value/)).not.toBeInTheDocument();
  ready();
  await user.click(screen.getByRole("button", { name: "Retry definitions" }));
  expect(await screen.findByRole("spinbutton", { name: "Amount" })).toHaveValue(
    42,
  );
});

it.each([
  { catalog: [] },
  { catalog: [{ ...sampleBlock, version: "9.0.0" }] },
  { catalog: [...blocks(), ...blocks()] },
  { catalog: [{ bad: "metadata" }] },
])(
  "handles unavailable, duplicate or malformed registry metadata accessibly",
  async ({ catalog }) => {
    server.use(http.get(url, () => HttpResponse.json(catalog)));
    seed({ amount: 42 });
    mount();
    await screen.findByRole("alert");
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(useEditorStore.getState().nodes[0].data.config).toEqual({
      amount: 42,
    });
  },
);

it("rejects unsupported and credential schemas without exposing stored runtime values", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json(
        blocks({
          type: "object",
          additionalProperties: false,
          properties: { password: { type: "string" } },
        }),
      ),
    ),
  );
  seed({ amount: 42 });
  mount();
  await screen.findByText(/unsupported or unsafe configuration schema/);
  expect(
    screen.queryByRole("textbox", { name: /password/i }),
  ).not.toBeInTheDocument();
  expect(() =>
    useEditorStore
      .getState()
      .setNodeConfiguration("first", { api_key: "fictional" }),
  ).toThrow();
  expect(() =>
    useEditorStore
      .getState()
      .setNodeConfiguration("first", { resource_ref: "C:\\private\\file" }),
  ).toThrow();
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    amount: 42,
  });
});

it("supports scalar lists, typed boolean and enum choices, null, and unfinished list edits", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json(
        blocks({
          type: "object",
          additionalProperties: false,
          properties: {
            columns: {
              type: "array",
              title: "Columns",
              items: { type: "string" },
              uniqueItems: true,
            },
            enabled: { type: "boolean", title: "Enabled" },
            mode: { type: "string", title: "Mode", enum: ["fill", "drop"] },
            optional: {
              title: "Optional",
              anyOf: [{ type: "string" }, { type: "null" }],
            },
          },
        }),
      ),
    ),
  );
  seed({});
  mount();
  const user = userEvent.setup();
  const list = await screen.findByRole("textbox", { name: "Columns" });
  await user.click(list);
  await user.paste('["a", "b"]');
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Enabled" }),
    "false",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Mode" }),
    '"drop"',
  );
  await user.click(
    screen.getByRole("button", { name: "Set Optional to null" }),
  );
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    columns: ["a", "b"],
    enabled: false,
    mode: "drop",
    optional: null,
  });
  await user.clear(list);
  await user.paste('["unfinished"');
  await user.click(screen.getByRole("button", { name: "Second" }));
  await user.click(screen.getByRole("button", { name: "First" }));
  expect(screen.getByRole("textbox", { name: "Columns" })).toHaveValue(
    '["unfinished"',
  );
  expect(screen.getByText("Enter a valid JSON list.")).toBeVisible();
});

it("keeps an empty selection usable and blocks edits during save or after node deletion", async () => {
  ready();
  mount();
  expect(screen.getByText("Select a block to configure it.")).toBeVisible();
  act(() => seed());
  await screen.findByRole("spinbutton", { name: "Amount" });
  act(() => useEditorStore.getState().setBusy(true));
  expect(amount()).toBeDisabled();
  act(() =>
    useEditorStore.getState().setNodeConfiguration("first", { amount: 99 }),
  );
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({ amount: 1 });
  act(() => {
    useEditorStore.getState().setBusy(false);
    useEditorStore.getState().deleteSelected();
    useEditorStore.getState().setNodeConfiguration("first", { amount: 99 });
  });
  await waitFor(() =>
    expect(screen.getByText("Select a block to configure it.")).toBeVisible(),
  );
  expect(useEditorStore.getState().nodes.map((n) => n.id)).toEqual(["second"]);
});

it("refuses unsafe defaults and conceals unsafe imported config without erasing it", async () => {
  ready();
  const store = useEditorStore.getState();
  store.addBlock({
    ...sampleBlock,
    config_schema: {
      type: "object",
      additionalProperties: false,
      properties: {
        resource_ref: { type: "string", default: "/private/input.csv" },
      },
    },
  });
  expect(useEditorStore.getState().nodes).toEqual([]);
  expect(useEditorStore.getState().error).toContain("runtime bindings");
  seed({ password: "fictional-private-value" });
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "configuration contains unsupported values or runtime bindings",
  );
  expect(
    screen.queryByDisplayValue("fictional-private-value"),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/fictional-private-value/)).not.toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    password: "fictional-private-value",
  });
});
