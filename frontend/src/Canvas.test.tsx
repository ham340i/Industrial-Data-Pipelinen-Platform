import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { Builder } from "./Builder";
import { server } from "./test/server";
import { rowCountBlock, sampleBlock } from "./test/blocks";
import { useEditorStore } from "./state/editor";

function renderBuilder() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={client}>
      <Builder />
    </QueryClientProvider>,
  );
}
it("discovers metadata and supports keyboard creation, selection and deletion", async () => {
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock, rowCountBlock]),
    ),
  );
  renderBuilder();
  const add = await screen.findByRole("button", {
    name: "Add Row Count",
  });
  expect(screen.getByText("Inputs: table (data)")).toBeVisible();
  add.focus();
  await userEvent.keyboard("{Enter}");
  expect(useEditorStore.getState().nodes).toHaveLength(1);
  expect(useEditorStore.getState().selectedNodeId).toBe(
    useEditorStore.getState().nodes[0].id,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Delete selected" }),
  );
  expect(useEditorStore.getState().nodes).toHaveLength(0);
});
it("retains the draft on library failure and retries", async () => {
  useEditorStore.getState().addBlock(rowCountBlock);
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () => HttpResponse.error()),
  );
  renderBuilder();
  const retry = await screen.findByRole("button", { name: "Retry library" });
  expect(useEditorStore.getState().nodes).toHaveLength(1);
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock, rowCountBlock]),
    ),
  );
  await userEvent.click(retry);
  expect(
    await screen.findByRole("button", { name: "Add Row Count" }),
  ).toBeVisible();
  expect(useEditorStore.getState().nodes).toHaveLength(1);
});

it("hides examples from browsing, search and drops while retaining saved nodes", async () => {
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock, rowCountBlock]),
    ),
  );
  useEditorStore.getState().loadSaved({
    id: "saved",
    project_id: "p",
    name: "Existing example",
    revision: 1,
    definition: {
      schema_version: 1,
      nodes: ["a", "b"].map((id) => ({
        id,
        block_id: sampleBlock.block_id,
        block_version: sampleBlock.version,
        config: { amount: 3 },
      })),
      edges: [],
      layout: { positions: { a: { x: 0, y: 0 }, b: { x: 300, y: 0 } } },
    },
  });
  useEditorStore.getState().selectNode("a");
  renderBuilder();
  await screen.findByRole("button", { name: "Add Row Count" });
  const library = within(
    screen.getByRole("heading", { name: "Block library" }).parentElement!,
  );
  expect(library.queryByText("Synthetic Add Constant")).not.toBeInTheDocument();
  await userEvent.type(
    screen.getByRole("textbox", { name: "Search blocks" }),
    "synthetic",
  );
  expect(
    library.queryByRole("button", { name: /^Add / }),
  ).not.toBeInTheDocument();

  const canvas = screen.getByLabelText("Pipeline canvas");
  expect(within(canvas).getAllByText("Synthetic Add Constant")).toHaveLength(2);
  const amount = await screen.findByRole("spinbutton", { name: "Amount" });
  expect(amount).toHaveValue(3);
  await userEvent.clear(amount);
  await userEvent.type(amount, "7");
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({ amount: 7 });
  act(() =>
    useEditorStore.getState().connect(
      {
        source: "a",
        target: "b",
        sourceHandle: "table",
        targetHandle: "table",
      },
      [sampleBlock, rowCountBlock],
    ),
  );
  expect(useEditorStore.getState().edges).toHaveLength(1);

  // A drag payload from an old tab cannot add a now-hidden block.
  fireEvent.drop(canvas, {
    dataTransfer: {
      getData: () =>
        JSON.stringify([sampleBlock.block_id, sampleBlock.version]),
    },
  });
  expect(useEditorStore.getState().nodes).toHaveLength(2);
});

it("shows an empty library when the catalog contains only hidden blocks", async () => {
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock]),
    ),
  );
  renderBuilder();
  expect(
    await screen.findByText("No blocks are available to add."),
  ).toBeVisible();
});
