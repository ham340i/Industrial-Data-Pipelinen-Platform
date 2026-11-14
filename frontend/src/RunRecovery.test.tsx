// AI contribution: 50% or more AI-generated
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { RunControls } from "./RunControls";
import { ConfigurationPanel } from "./configuration/ConfigurationPanel";
import { server } from "./test/server";
import { sampleBlock } from "./test/blocks";
import { useEditorStore } from "./state/editor";

const project = "11111111-1111-4111-8111-111111111111";
const pipeline = "22222222-2222-4222-8222-222222222222";
const runId = "33333333-3333-4333-8333-333333333333";
const executeUrl = `http://127.0.0.1:8000/api/v1/projects/${project}/pipelines/${pipeline}/execute`;
const detailUrl = `http://127.0.0.1:8000/api/v1/runs/${runId}`;
const failure = { code: "sql_query_failed", reason: "Read query failed." };
const timestamp = "2026-11-12T23:00:00.000Z";
const result = {
  schema_version: 1,
  id: runId,
  project_id: project,
  pipeline_id: pipeline,
  pipeline_revision_id: "55555555-5555-4555-8555-555555555555",
  revision: 1,
  state: "failed",
  created_at: timestamp,
  started_at: timestamp,
  ended_at: timestamp,
  duration_ms: 0,
  row_count: 0,
  error: failure,
  blocks: [
    {
      position: 0,
      node_id: "sql",
      block_id: sampleBlock.block_id,
      block_version: sampleBlock.version,
      state: "failed",
      started_at: timestamp,
      ended_at: timestamp,
      duration_ms: 0,
      rows_in: null,
      rows_out: 0,
      error: failure,
    },
  ],
  events: [],
  outputs: [],
};
const run = () => screen.getByRole("button", { name: "Run saved pipeline" });
function setup() {
  useEditorStore.getState().setProject(project);
  useEditorStore.getState().loadSaved({
    id: pipeline,
    project_id: project,
    name: "Saved source",
    revision: 1,
    definition: {
      schema_version: 1,
      nodes: [
        {
          id: "sql",
          block_id: sampleBlock.block_id,
          block_version: sampleBlock.version,
          config: { amount: 42 },
        },
      ],
      edges: [],
      layout: { positions: { sql: { x: 0, y: 0 } } },
    },
  });
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
      <RunControls canRun />
      <ConfigurationPanel />
    </QueryClientProvider>,
  );
}
function failedRun(patch = {}) {
  const posts: unknown[] = [];
  server.use(
    http.post(executeUrl, async ({ request }) => {
      posts.push(await request.json());
      return HttpResponse.json({ run_id: runId, state: "failed" });
    }),
    http.get(detailUrl, () => HttpResponse.json({ ...result, ...patch })),
  );
  return posts;
}

it("sends the opened revision and focuses failed block settings without changing the graph", async () => {
  const posts = failedRun();
  setup();
  const before = structuredClone(useEditorStore.getState().nodes);
  await userEvent.click(run());
  const configure = await screen.findByRole("button", {
    name: "Configure failed block sql",
  });
  expect(posts).toEqual([{ expected_revision: 1 }]);
  expect(
    screen.getByRole("status", { name: "Execution status" }),
  ).toHaveFocus();
  configure.focus();
  await userEvent.keyboard("{Enter}");
  expect(
    await screen.findByRole("spinbutton", { name: "Amount" }),
  ).toHaveFocus();
  expect(
    useEditorStore
      .getState()
      .nodes.map(({ id, data, position }) => ({ id, data, position })),
  ).toEqual(before.map(({ id, data, position }) => ({ id, data, position })));
});

it("retries a result read from the keyboard without executing again or exposing the raw body", async () => {
  let gets = 0;
  const posts = failedRun();
  server.use(
    http.get(detailUrl, () =>
      ++gets === 1
        ? HttpResponse.json(
            { error: { message: "token=private-value C:/private/database" } },
            { status: 500 },
          )
        : HttpResponse.json(result),
    ),
  );
  setup();
  const nodes = useEditorStore.getState().nodes;
  await userEvent.click(run());
  const retry = await screen.findByRole("button", {
    name: "Retry run results",
  });
  expect(
    screen.queryByText(/private-value|private\/database/),
  ).not.toBeInTheDocument();
  retry.focus();
  await userEvent.keyboard("{Enter}");
  await screen.findByRole("button", { name: "Configure failed block sql" });
  expect(
    screen.getByRole("status", { name: "Execution status" }),
  ).toHaveFocus();
  expect(posts).toHaveLength(1);
  expect(gets).toBe(2);
  expect(useEditorStore.getState().nodes).toBe(nodes);
});

it("keeps run status and evidence during a poll and after a failed refresh", async () => {
  const posts = failedRun();
  let finishPoll!: () => void;
  const poll = new Promise<void>((resolve) => {
    finishPoll = resolve;
  });
  let reads = 0;
  server.use(
    http.get(detailUrl, async () => {
      reads += 1;
      if (reads === 1)
        return HttpResponse.json({
          ...result,
          state: "running",
          ended_at: null,
          duration_ms: null,
          row_count: null,
          error: null,
          blocks: [],
          events: [
            {
              sequence: 1,
              created_at: timestamp,
              level: "info",
              node_id: null,
              kind: "run_started",
              code: null,
              message: "Execution started.",
            },
          ],
        });
      if (reads === 2) {
        await poll;
        return new HttpResponse(null, { status: 503 });
      }
      return HttpResponse.json(result);
    }),
  );
  setup();
  await userEvent.click(run());
  const status = screen.getByRole("status", { name: "Execution status" });
  await screen.findByText("Execution started.");
  await waitFor(() => expect(reads).toBe(2), { timeout: 2000 });
  expect(status).toHaveTextContent("Run running");
  finishPoll();
  const retry = await screen.findByRole("button", {
    name: "Retry run results",
  });
  expect(status).toHaveTextContent("Run running");
  expect(screen.getByText("Execution started.")).toBeVisible();
  expect(screen.getByText(/last loaded run results/)).toBeVisible();
  await userEvent.click(retry);
  await screen.findByText(/Run failed.*revision 1/);
  expect(screen.queryByText("Execution started.")).not.toBeInTheDocument();
  expect(posts).toHaveLength(1);
});

it("keeps unsaved edits and does not navigate a late failure into a changed draft", async () => {
  failedRun();
  let resolve!: () => void;
  const response = {
    promise: new Promise<void>((done) => {
      resolve = done;
    }),
    resolve: () => resolve(),
  };
  let reading = false;
  server.use(
    http.get(detailUrl, async () => {
      reading = true;
      await response.promise;
      return HttpResponse.json(result);
    }),
  );
  setup();
  await userEvent.click(run());
  await waitFor(() => expect(reading).toBe(true));
  act(() =>
    useEditorStore.getState().setNodeConfiguration("sql", { amount: 77 }),
  );
  response.resolve();
  await screen.findByText(/Run failed.*revision 1/);
  expect(
    screen.queryByRole("button", { name: "Configure failed block sql" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/different saved revision or draft/)).toBeVisible();
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    amount: 77,
  });
  expect(useEditorStore.getState().selectedNodeId).toBeNull();
});

it.each([
  { revision: 2 },
  { blocks: [{ ...result.blocks[0], node_id: "removed" }] },
])(
  "does not offer misleading configuration targets for mismatched evidence %j",
  async (patch) => {
    failedRun(patch);
    setup();
    await userEvent.click(run());
    await screen.findByText(/Run failed.*revision/);
    expect(
      screen.queryByRole("button", { name: /Configure failed block/ }),
    ).not.toBeInTheDocument();
    expect(useEditorStore.getState().revision).toBe(1);
  },
);

it("discards a late execution response after switching projects", async () => {
  let resolve!: () => void;
  const response = {
    promise: new Promise<void>((done) => {
      resolve = done;
    }),
    resolve: () => resolve(),
  };
  let started = false;
  server.use(
    http.post(executeUrl, async () => {
      started = true;
      await response.promise;
      return HttpResponse.json({ run_id: runId, state: "failed" });
    }),
  );
  setup();
  await userEvent.click(run());
  await waitFor(() => expect(started).toBe(true));
  act(() =>
    useEditorStore
      .getState()
      .setProject("44444444-4444-4444-8444-444444444444"),
  );
  response.resolve();
  await new Promise((resolve) => setTimeout(resolve, 30));
  expect(screen.queryByText(/Run failed/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Loading run results/)).not.toBeInTheDocument();
  expect(useEditorStore.getState().nodes).toEqual([]);
});

it("reports revision conflicts without exposing response text or replacing edits", async () => {
  server.use(
    http.post(executeUrl, () =>
      HttpResponse.json(
        {
          error: {
            code: "revision_conflict",
            message: "secret=synthetic C:/private",
            node_context: null,
          },
        },
        { status: 409 },
      ),
    ),
  );
  setup();
  await userEvent.click(run());
  expect(await screen.findByText(/changed since it was opened/)).toBeVisible();
  expect(screen.queryByText(/secret=|C:\/private/)).not.toBeInTheDocument();
  expect(useEditorStore.getState().revision).toBe(1);
  expect(useEditorStore.getState().nodes[0].data.config).toEqual({
    amount: 42,
  });
});

it("navigates a structured refused-run node without reflecting its private error text", async () => {
  server.use(
    http.post(executeUrl, () =>
      HttpResponse.json(
        {
          error: {
            code: "missing_input",
            message: "password=synthetic",
            node_context: "sql",
          },
        },
        { status: 422 },
      ),
    ),
  );
  setup();
  await userEvent.click(run());
  const configure = await screen.findByRole("button", {
    name: "Configure blocked node sql",
  });
  expect(screen.queryByText(/password=/)).not.toBeInTheDocument();
  configure.focus();
  await userEvent.keyboard("{Enter}");
  expect(
    await screen.findByRole("spinbutton", { name: "Amount" }),
  ).toHaveFocus();
});

it("reports an HTTP rejection without suggesting it started a run", async () => {
  server.use(
    http.post(executeUrl, () =>
      HttpResponse.json({ detail: "secret=synthetic" }, { status: 404 }),
    ),
  );
  setup();
  await userEvent.click(run());
  expect(await screen.findByText(/rejected.*HTTP 404/)).toBeVisible();
  expect(
    screen.queryByText(/may have started a run|secret=/),
  ).not.toBeInTheDocument();
});

it.each(["network", "malformed", "server"] as const)(
  "does not automatically repeat an uncertain %s execution",
  async (kind) => {
    let posts = 0;
    server.use(
      http.post(executeUrl, () => {
        posts += 1;
        if (kind === "network") return HttpResponse.error();
        return HttpResponse.json(
          { run_id: "invalid", message: "secret=synthetic" },
          { status: kind === "server" ? 500 : 200 },
        );
      }),
    );
    setup();
    const before = useEditorStore.getState().nodes;
    await userEvent.click(run());
    expect(await screen.findByText(/may have started a run/)).toBeVisible();
    expect(screen.queryByText(/secret=/)).not.toBeInTheDocument();
    expect(posts).toBe(1);
    expect(useEditorStore.getState().nodes).toBe(before);
    expect(
      screen.queryByRole("button", { name: /Configure/ }),
    ).not.toBeInTheDocument();
  },
);

it("discards a late run read after reopening the same pipeline revision", async () => {
  failedRun();
  let resolve!: () => void;
  const response = new Promise<void>((done) => {
    resolve = done;
  });
  let reading = false;
  server.use(
    http.get(detailUrl, async () => {
      reading = true;
      await response;
      return HttpResponse.json(result);
    }),
  );
  setup();
  await userEvent.click(run());
  await waitFor(() => expect(reading).toBe(true));
  act(() =>
    useEditorStore.getState().loadSaved({
      id: pipeline,
      project_id: project,
      name: "Reopened",
      revision: 1,
      definition: {
        schema_version: 1,
        nodes: [],
        edges: [],
        layout: { positions: {} },
      },
    }),
  );
  resolve();
  await waitFor(() =>
    expect(
      screen.getByRole("status", { name: "Execution status" }),
    ).toHaveTextContent("No run requested."),
  );
  expect(
    screen.queryByRole("button", { name: /Configure failed/ }),
  ).not.toBeInTheDocument();
  expect(useEditorStore.getState().draftName).toBe("Reopened");
  expect(useEditorStore.getState().nodes).toEqual([]);
});
