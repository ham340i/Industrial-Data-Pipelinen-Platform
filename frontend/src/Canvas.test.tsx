import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { Builder } from "./Builder";
import { server } from "./test/server";
import { sampleBlock } from "./test/blocks";
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
      HttpResponse.json([sampleBlock]),
    ),
  );
  renderBuilder();
  const add = await screen.findByRole("button", {
    name: "Add Synthetic Add Constant",
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
  useEditorStore.getState().addBlock(sampleBlock);
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () => HttpResponse.error()),
  );
  renderBuilder();
  const retry = await screen.findByRole("button", { name: "Retry library" });
  expect(useEditorStore.getState().nodes).toHaveLength(1);
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock]),
    ),
  );
  await userEvent.click(retry);
  expect(
    await screen.findByRole("button", { name: "Add Synthetic Add Constant" }),
  ).toBeVisible();
  expect(useEditorStore.getState().nodes).toHaveLength(1);
});
