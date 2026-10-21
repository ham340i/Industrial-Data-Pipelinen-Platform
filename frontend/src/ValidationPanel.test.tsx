import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { Builder } from "./Builder";
import type { SemanticDefinition } from "./api/validation";
import { server } from "./test/server";
import { sampleBlock } from "./test/blocks";
import { useEditorStore } from "./state/editor";

const url = "http://127.0.0.1:8000/api/v1/pipelines/validate";
const run = () => screen.getByRole("button", { name: "Run pipeline" });

function renderBuilder() {
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([sampleBlock]),
    ),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <Builder />
    </QueryClientProvider>,
  );
}
/**
 * Stand-in for the backend: answers with canned diagnostics addressed to the
 * IDs in the request. Rule behaviour itself is covered by the backend matrix.
 */
function backend(
  answer: (d: SemanticDefinition) => { code: string; [k: string]: unknown }[],
) {
  const requests: SemanticDefinition[] = [];
  server.use(
    http.post(url, async ({ request }) => {
      const { definition } = (await request.json()) as {
        definition: SemanticDefinition;
      };
      requests.push(definition);
      const diagnostics = answer(definition).map((d) => ({
        message: "Fix it.",
        node_id: null,
        edge_id: null,
        port: null,
        field: null,
        ...d,
      }));
      return HttpResponse.json({ valid: !diagnostics.length, diagnostics });
    }),
  );
  return requests;
}
const twoNodes = () => {
  useEditorStore.getState().addBlock(sampleBlock, { x: 0, y: 0 });
  useEditorStore.getState().addBlock(sampleBlock, { x: 300, y: 0 });
  return useEditorStore.getState().nodes.map((n) => n.id);
};

it("shows each problem on its node and in the list, keeps edits and disables running", async () => {
  const [a, b] = twoNodes();
  backend(() => [
    { code: "empty_pipeline", message: "Add at least one block." },
    {
      code: "invalid_config",
      node_id: a,
      field: "amount",
      message: "Fix 'amount': Input should be less than or equal to 1000.",
    },
    {
      code: "missing_input",
      node_id: b,
      port: "table",
      message: "Connect an upstream output to the required input 'table'.",
    },
  ]);
  const before = structuredClone(useEditorStore.getState().nodes);
  renderBuilder();
  expect(
    await screen.findByText("3 problems must be fixed before running."),
  ).toBeVisible();
  expect(run()).toBeDisabled();

  const list = screen.getByRole("list", { name: "Pipeline problems" });
  const items = within(list).getAllByRole("button");
  expect(items.map((i) => i.textContent)).toEqual([
    "Add at least one block.Pipeline",
    "Fix 'amount': Input should be less than or equal to 1000.Synthetic Add Constant",
    "Connect an upstream output to the required input 'table'.Synthetic Add Constant",
  ]);
  // Nodes sit inside React Flow's role="button" wrappers, so query by label.
  const cards = await screen.findAllByLabelText(
    "Problems in Synthetic Add Constant",
  );
  expect(cards.map((c) => c.textContent)).toEqual([
    "Fix 'amount': Input should be less than or equal to 1000.",
    "Connect an upstream output to the required input 'table'.",
  ]);

  await userEvent.click(items[2]);
  expect(useEditorStore.getState().selectedNodeId).toBe(b);
  const after = useEditorStore.getState().nodes;
  expect(
    after.map(({ id, data, position }) => ({ id, data, position })),
  ).toEqual(before.map(({ id, data, position }) => ({ id, data, position })));
});

it("re-checks after a fix and enables running only for the current valid graph", async () => {
  const [a, b] = twoNodes();
  const requests = backend((d) =>
    d.edges.length
      ? []
      : [{ code: "missing_input", node_id: b, port: "table" }],
  );
  renderBuilder();
  await screen.findByText("1 problem must be fixed before running.");
  expect(run()).toBeDisabled();

  act(() =>
    useEditorStore
      .getState()
      .connect(
        { source: a, target: b, sourceHandle: "table", targetHandle: "table" },
        [sampleBlock],
      ),
  );
  // Until the new graph has been checked, the old answer cannot enable Run.
  expect(screen.getByText("Checking pipeline…")).toBeVisible();
  expect(run()).toBeDisabled();
  expect(
    await screen.findByText("Ready to run. No problems found."),
  ).toBeVisible();
  expect(run()).toBeEnabled();
  expect(requests.at(-1)?.edges).toHaveLength(1);
  expect(useEditorStore.getState().nodes.map((n) => n.id)).toEqual([a, b]);

  await userEvent.click(run());
  expect(await screen.findByText(/The pipeline is valid/)).toBeVisible();
});

it("moving nodes does not trigger a new check", async () => {
  const [a] = twoNodes();
  const requests = backend(() => []);
  renderBuilder();
  await screen.findByText("Ready to run. No problems found.");
  const count = requests.length;
  act(() =>
    useEditorStore
      .getState()
      .changeNodes([{ type: "position", id: a, position: { x: 50, y: 70 } }]),
  );
  await new Promise((resolve) => setTimeout(resolve, 400));
  expect(requests).toHaveLength(count);
  expect(run()).toBeEnabled();
});

it("keeps running disabled when the check fails and keeps the draft", async () => {
  twoNodes();
  server.use(http.post(url, () => HttpResponse.error()));
  renderBuilder();
  expect(
    await screen.findByText(/Running stays disabled until the check succeeds/),
  ).toBeVisible();
  expect(run()).toBeDisabled();
  expect(useEditorStore.getState().nodes).toHaveLength(2);
});

it("a slow stale answer never enables running for a newer graph", async () => {
  const [a, b] = twoNodes();
  server.use(
    http.post(url, async ({ request }) => {
      const { definition } = (await request.json()) as {
        definition: SemanticDefinition;
      };
      if (definition.edges.length) {
        await delay(600);
        return HttpResponse.json({
          valid: false,
          diagnostics: [
            {
              code: "cycle",
              message: "This connection is part of a cycle.",
              node_id: a,
              edge_id: definition.edges[0].id,
              port: null,
              field: null,
            },
          ],
        });
      }
      return HttpResponse.json({ valid: true, diagnostics: [] });
    }),
  );
  renderBuilder();
  await screen.findByText("Ready to run. No problems found.");
  act(() =>
    useEditorStore
      .getState()
      .connect(
        { source: a, target: b, sourceHandle: "table", targetHandle: "table" },
        [sampleBlock],
      ),
  );
  expect(run()).toBeDisabled();
  await waitFor(
    () =>
      expect(
        screen.getByText("1 problem must be fixed before running."),
      ).toBeVisible(),
    { timeout: 2000 },
  );
  expect(run()).toBeDisabled();
  expect(screen.getByText("This connection is part of a cycle.")).toBeVisible();
});
