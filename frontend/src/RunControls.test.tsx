// AI contribution: 50% or more AI-generated
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { RunControls } from "./RunControls";
import { server } from "./test/server";
import { useEditorStore } from "./state/editor";

const project = "11111111-1111-4111-8111-111111111111";
const pipeline = "22222222-2222-4222-8222-222222222222";
const run = "33333333-3333-4333-8333-333333333333";
function setup(canRun = true) {
  useEditorStore.getState().setProject(project);
  useEditorStore.getState().loadSaved({
    id: pipeline,
    project_id: project,
    name: "SQL",
    revision: 1,
    definition: {
      schema_version: 1,
      nodes: [],
      edges: [],
      layout: { positions: {} },
    },
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <RunControls canRun={canRun} />
    </QueryClientProvider>,
  );
}
it("requires current validation and a saved graph", () => {
  setup(false);
  expect(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  ).toBeDisabled();
});
it("disables execution after an edit", () => {
  setup();
  act(() => useEditorStore.getState().setDraftName("Edited"));
  expect(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  ).toBeDisabled();
});
it("shows run evidence and useful block failures", async () => {
  server.use(
    http.post(
      `http://127.0.0.1:8000/api/v1/projects/${project}/pipelines/${pipeline}/execute`,
      () => HttpResponse.json({ run_id: run, state: "failed" }),
    ),
    http.get(`http://127.0.0.1:8000/api/v1/runs/${run}`, () =>
      HttpResponse.json({
        schema_version: 1,
        id: run,
        project_id: project,
        pipeline_id: pipeline,
        revision: 1,
        state: "failed",
        duration_ms: 0,
        row_count: 0,
        error: { code: "sql_query_failed", reason: "Read query failed." },
        blocks: [
          {
            node_id: "sql",
            state: "failed",
            duration_ms: 0,
            rows_in: null,
            rows_out: 0,
            error: null,
          },
        ],
        events: [{ sequence: 1, message: "Block failed." }],
        outputs: [],
      }),
    ),
  );
  setup();
  await userEvent.click(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  );
  await screen.findByText("Run failed · revision 1");
  expect(screen.getByText("Duration: 0 ms · Output rows: 0")).toBeVisible();
  expect(screen.getByText("Block failed.")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent("sql_query_failed");
  expect(useEditorStore.getState().busy).toBe(false);
});
it("retains the saved graph after a request fails", async () => {
  server.use(
    http.post(
      `http://127.0.0.1:8000/api/v1/projects/${project}/pipelines/${pipeline}/execute`,
      () => HttpResponse.json({}, { status: 422 }),
    ),
  );
  setup();
  await userEvent.click(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  );
  await screen.findByText(/Your saved pipeline is retained/);
  expect(useEditorStore.getState().pipelineId).toBe(pipeline);
  expect(
    screen.getByRole("button", { name: "Run saved pipeline" }),
  ).toBeEnabled();
});
