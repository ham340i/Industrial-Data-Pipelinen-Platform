// AI contribution: 50% or more AI-generated
import {
  onlineManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it, vi } from "vitest";
import { RunMonitor } from "./RunMonitor";
import { RunControls } from "./RunControls";
import { getRun, listRuns } from "./api/runs";
import { useEditorStore } from "./state/editor";
import { server } from "./test/server";
import { api } from "./api/client";

const base = "http://127.0.0.1:8000/api/v1";
const project = "11111111-1111-4111-8111-111111111111";
const pipeline = "22222222-2222-4222-8222-222222222222";
const first = "33333333-3333-4333-8333-333333333333";
const second = "44444444-4444-4444-8444-444444444444";
const stamp = "2026-11-10T12:00:00Z";
function evidence(id = first, state = "succeeded") {
  return {
    schema_version: 1,
    id,
    project_id: project,
    pipeline_id: pipeline,
    pipeline_revision_id: pipeline,
    revision: 1,
    state,
    created_at: stamp,
    started_at: null,
    ended_at: null,
    duration_ms: null,
    row_count: 0,
    error: null,
    blocks: [
      {
        position: 0,
        node_id: "source",
        block_id: "source.csv",
        block_version: "1.0.0",
        state: "completed",
        started_at: null,
        ended_at: null,
        duration_ms: 0,
        rows_in: null,
        rows_out: 0,
        error: null,
      },
    ],
    events: [],
    outputs: [],
  };
}
function setup(items = [evidence()]) {
  server.use(
    http.get(`${base}/runs`, () =>
      HttpResponse.json({ items, total: items.length, offset: 0, limit: 20 }),
    ),
    http.get(`${base}/runs/:id`, ({ params }) =>
      HttpResponse.json(evidence(String(params.id))),
    ),
  );
}
function mount(withControls = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const result = render(
    <QueryClientProvider client={client}>
      {withControls && <RunControls canRun />}
      <RunMonitor key={pipeline} projectId={project} pipelineId={pipeline} />
    </QueryClientProvider>,
  );
  return { ...result, client };
}
it("shows empty and loading feedback", async () => {
  setup([]);
  mount();
  expect(screen.getByText("Loading runs…")).toBeVisible();
  expect(await screen.findByText(/No runs yet/)).toBeVisible();
});
it("refreshes history and the selected run with one button", async () => {
  let lists = 0;
  let selectedReads = 0;
  setup([evidence(), evidence(second)]);
  server.use(
    http.get(`${base}/runs`, () => {
      lists += 1;
      return HttpResponse.json({
        items: [evidence(), evidence(second)],
        total: 2,
        offset: 0,
        limit: 20,
      });
    }),
    http.get(`${base}/runs/${second}`, () => {
      selectedReads += 1;
      return HttpResponse.json({
        ...evidence(second),
        row_count: selectedReads,
      });
    }),
  );
  mount();
  await screen.findByText(`Completed · Run ${first}`);
  await userEvent.selectOptions(screen.getByLabelText("Selected run"), second);
  await screen.findByText(`Completed · Run ${second}`);
  const refresh = screen.getAllByRole("button", { name: /^Refresh run/ });
  expect(refresh).toHaveLength(1);
  const initialLists = lists;
  const initialReads = selectedReads;
  await userEvent.click(refresh[0]);
  await waitFor(() => expect(lists).toBeGreaterThan(initialLists));
  await waitFor(() => expect(selectedReads).toBeGreaterThan(initialReads));
  expect(screen.getByLabelText("Selected run")).toHaveValue(second);
  expect(screen.getByText(/Saved revision 1/)).toHaveTextContent(
    `Rows: ${selectedReads}`,
  );
});
it("keeps one download button for the selected historical run after execution", async () => {
  useEditorStore.getState().setProject(project);
  useEditorStore.getState().loadSaved({
    id: pipeline,
    project_id: project,
    name: "Saved pipeline",
    revision: 1,
    definition: {
      schema_version: 1,
      nodes: [],
      edges: [],
      layout: { positions: {} },
    },
  });
  setup([evidence(), evidence(second)]);
  server.use(
    http.post(`${base}/projects/${project}/pipelines/${pipeline}/execute`, () =>
      HttpResponse.json({ run_id: first, state: "succeeded" }),
    ),
  );
  mount(true);
  await screen.findByText(`Completed · Run ${first}`);
  await userEvent.click(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  );
  await screen.findByText("Run succeeded · revision 1");
  await userEvent.selectOptions(screen.getByLabelText("Selected run"), second);
  await screen.findByText(`Completed · Run ${second}`);
  expect(screen.getAllByRole("button", { name: "Download log" })).toHaveLength(
    1,
  );
  const createUrl = vi.fn(() => "blob:log");
  const revokeUrl = vi.fn();
  vi.stubGlobal(
    "URL",
    Object.assign(URL, {
      createObjectURL: createUrl,
      revokeObjectURL: revokeUrl,
    }),
  );
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  const request = vi.spyOn(api, "get").mockResolvedValueOnce({
    data: new Blob(["Selected run log"]),
  } as Awaited<ReturnType<typeof api.get>>);
  await userEvent.click(screen.getByRole("button", { name: "Download log" }));
  expect(request).toHaveBeenCalledWith(`/runs/${second}/log`, {
    responseType: "blob",
  });
  await waitFor(() => expect(revokeUrl).toHaveBeenCalledOnce());
});
it.each(["queued", "running", "succeeded", "failed", "cancelled"])(
  "renders %s with real zeros distinct from unknown",
  async (state) => {
    setup();
    server.use(
      http.get(`${base}/runs/:id`, () =>
        HttpResponse.json(evidence(first, state)),
      ),
    );
    mount();
    const status = await screen.findByText(new RegExp(`Run ${first}`));
    expect(status).toHaveTextContent(
      state === "succeeded"
        ? "Completed"
        : state[0].toUpperCase() + state.slice(1),
    );
    expect(screen.getByText(/Saved revision 1/)).toHaveTextContent(
      "Duration: Unknown · Rows: 0",
    );
    expect(
      screen.queryByRole("region", { name: "Block source" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download log" })).toBeEnabled();
  },
);
it("isolates a late response after selecting another run and collects old queries", async () => {
  setup([evidence(), evidence(second)]);
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.get(`${base}/runs/${first}`, async () => {
      await pending;
      return HttpResponse.json(evidence());
    }),
  );
  const { client } = mount();
  await userEvent.selectOptions(
    await screen.findByLabelText("Selected run"),
    second,
  );
  expect(await screen.findByText(`Completed · Run ${second}`)).toBeVisible();
  finish();
  await act(async () => {
    await pending;
  });
  expect(
    screen.queryByText(`Completed · Run ${first}`),
  ).not.toBeInTheDocument();
  await waitFor(() =>
    expect(
      client.getQueryData(["run", project, pipeline, first]),
    ).toBeUndefined(),
  );
});
it("rejects cross-run and cross-pipeline evidence", async () => {
  setup();
  server.use(
    http.get(`${base}/runs/:id`, () => HttpResponse.json(evidence(second))),
  );
  await expect(getRun(project, pipeline, first)).rejects.toThrow(/mismatched/);
  await expect(listRuns(project, first)).rejects.toThrow(/mismatched/);
});
it("marks retained data stale and recovers by refreshing", async () => {
  setup();
  mount();
  await screen.findByText(`Completed · Run ${first}`);
  server.use(
    http.get(`${base}/runs/:id`, () => new HttpResponse(null, { status: 503 })),
  );
  await userEvent.click(screen.getByRole("button", { name: "Refresh runs" }));
  expect(await screen.findByText(/Displayed evidence is stale/)).toBeVisible();
  setup();
  await userEvent.click(screen.getByRole("button", { name: "Refresh runs" }));
  await waitFor(() =>
    expect(
      screen.queryByText(/Displayed evidence is stale/),
    ).not.toBeInTheDocument(),
  );
});
it("downloads logs without displaying events and navigates failed blocks safely", async () => {
  setup();
  useEditorStore.setState({
    projectId: project,
    pipelineId: pipeline,
    revision: 1,
    nodes: [
      {
        id: "source",
        type: "block",
        position: { x: 10, y: 20 },
        data: {
          block_id: "source.csv",
          block_version: "1.0.0",
          config: { resource_ref: "missing.csv" },
        },
      },
    ],
  });
  const before = structuredClone(useEditorStore.getState().nodes);
  const run = {
    ...evidence(first, "failed"),
    error: { code: "block_failed", reason: "Check input resource." },
    blocks: evidence().blocks.map((block) => ({
      ...block,
      state: "failed",
      error: { code: "resource_missing", reason: "Check input resource." },
    })),
    events: Array.from({ length: 150 }, (_, sequence) => ({
      sequence,
      created_at: stamp,
      level: "error",
      node_id: null,
      kind: "failure",
      code: null,
      message: `<script>event-${sequence}</script> [REDACTED]`,
    })),
  };
  server.use(http.get(`${base}/runs/:id`, () => HttpResponse.json(run)));
  mount();
  await screen.findByText(`Failed · Run ${first}`);
  expect(
    screen.queryByRole("list", { name: "Run log events" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/event-149/)).not.toBeInTheDocument();
  const createUrl = vi.fn(() => "blob:log");
  const revokeUrl = vi.fn();
  vi.stubGlobal(
    "URL",
    Object.assign(URL, {
      createObjectURL: createUrl,
      revokeObjectURL: revokeUrl,
    }),
  );
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
  vi.spyOn(api, "get").mockResolvedValueOnce({
    data: new Blob(["Complete run log"]),
  } as Awaited<ReturnType<typeof api.get>>);
  server.use(
    http.get(
      `${base}/runs/${first}/log`,
      () =>
        new HttpResponse("Complete run log", {
          headers: { "Content-Type": "text/plain" },
        }),
    ),
  );
  await userEvent.click(screen.getByRole("button", { name: "Download log" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Download log" })).toBeEnabled(),
  );
  expect(
    screen.queryAllByRole("alert").map((element) => element.textContent),
  ).toEqual(["block_failed: Check input resource."]);
  expect(createUrl).toHaveBeenCalledOnce();
  expect(click).toHaveBeenCalledOnce();
  await userEvent.click(
    screen.getByRole("button", { name: "Configure failed block source" }),
  );
  expect(useEditorStore.getState().configFocus).toEqual({
    nodeId: "source",
    field: null,
  });
  expect(
    useEditorStore.getState().nodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
    })),
  ).toEqual(before);
  act(() => useEditorStore.setState({ nodes: [] }));
  expect(
    screen.queryByRole("button", { name: "Configure failed block source" }),
  ).not.toBeInTheDocument();
});
it("polls active details to completion", async () => {
  setup();
  let reads = 0;
  server.use(
    http.get(`${base}/runs/:id`, () =>
      HttpResponse.json(
        evidence(first, ++reads === 1 ? "running" : "succeeded"),
      ),
    ),
  );
  mount();
  await screen.findByText(`Running · Run ${first}`);
  await screen.findByText(`Completed · Run ${first}`, {}, { timeout: 3500 });
  expect(reads).toBe(2);
});
it("rejects malformed measurements and events instead of fabricating evidence", async () => {
  setup();
  for (const patch of [
    { duration_ms: -1 },
    { row_count: "0" },
    { state: "unknown" },
    { events: [{ sequence: 1 }] },
  ]) {
    server.use(
      http.get(`${base}/runs/:id`, () =>
        HttpResponse.json({ ...evidence(), ...patch }),
      ),
    );
    await expect(getRun(project, pipeline, first)).rejects.toThrow(
      /unsupported/,
    );
  }
});

it("keeps an explicit selection when a newer run arrives and reconnects", async () => {
  setup([evidence(), evidence(second)]);
  mount();
  await userEvent.selectOptions(
    await screen.findByLabelText("Selected run"),
    second,
  );
  await screen.findByText(`Completed · Run ${second}`);
  act(() => onlineManager.setOnline(false));
  expect(screen.getByText(/Offline. Displayed evidence/)).toBeVisible();
  setup([evidence()]);
  try {
    act(() => onlineManager.setOnline(true));
    await waitFor(() =>
      expect(
        screen.getByRole("option", { name: `${second} (selected history)` }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(`Completed · Run ${second}`)).toBeVisible();
  } finally {
    onlineManager.setOnline(true);
  }
});
it("clears evidence on switching pipeline scope", async () => {
  setup();
  const { rerender, client } = mount();
  await screen.findByText(`Completed · Run ${first}`);
  server.use(
    http.get(`${base}/runs`, () =>
      HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
    ),
  );
  rerender(
    <QueryClientProvider client={client}>
      <RunMonitor key={second} projectId={project} pipelineId={second} />
    </QueryClientProvider>,
  );
  expect(
    screen.queryByText(`Completed · Run ${first}`),
  ).not.toBeInTheDocument();
  expect(await screen.findByText(/No runs yet/)).toBeVisible();
});
