import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { PipelineControls } from "./PipelineControls";
import { server } from "./test/server";
import { sampleBlock } from "./test/blocks";
import { useEditorStore } from "./state/editor";
import { serializeGraph } from "./state/graph";
import type { SavedPipeline } from "./api/pipelines";

const project = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const url = `http://127.0.0.1:8000/api/v1/projects/${project}/pipelines`;
function setup() {
  useEditorStore.getState().setProject(project);
  useEditorStore.getState().setDraftName("Inspection");
  useEditorStore.getState().addBlock(sampleBlock, { x: 23, y: -45 });
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <PipelineControls projectId={project} />
    </QueryClientProvider>,
  );
}
it("saves, renames and reopens identical configuration and positions", async () => {
  let saved: SavedPipeline | undefined;
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as Pick<
        SavedPipeline,
        "name" | "definition"
      >;
      saved = { ...body, id, project_id: project, revision: 1 };
      return HttpResponse.json(saved, { status: 201 });
    }),
    http.put(`${url}/${id}`, async ({ request }) => {
      const body = (await request.json()) as Pick<
        SavedPipeline,
        "name" | "definition"
      > & { expected_revision: number };
      expect(body.expected_revision).toBe(1);
      saved = { ...body, id, project_id: project, revision: 2 };
      return HttpResponse.json(saved);
    }),
    http.get(url, () =>
      HttpResponse.json({
        items: saved ? [saved] : [],
        total: saved ? 1 : 0,
        offset: 0,
        limit: 20,
      }),
    ),
    http.get(`${url}/${id}`, () => HttpResponse.json(saved)),
  );
  setup();
  const s = useEditorStore.getState(),
    original = serializeGraph(s.nodes, s.edges);
  await userEvent.click(screen.getByRole("button", { name: "Save pipeline" }));
  await screen.findByText("Pipeline saved.");
  expect(saved?.definition).toEqual(original);
  act(() => useEditorStore.getState().setDraftName("Renamed"));
  await userEvent.click(screen.getByRole("button", { name: "Save pipeline" }));
  await screen.findByText("Revision 2 · Saved");
  act(() => useEditorStore.getState().clearDraft());
  await userEvent.click(
    await screen.findByRole("button", { name: "Open Renamed (revision 2)" }),
  );
  await screen.findByText("Pipeline opened.");
  const loaded = useEditorStore.getState();
  expect(loaded.draftName).toBe("Renamed");
  expect(serializeGraph(loaded.nodes, loaded.edges)).toEqual(original);
});
it("keeps unsaved changes after a conflict", async () => {
  server.use(http.post(url, () => HttpResponse.json({}, { status: 409 })));
  setup();
  const before = useEditorStore.getState().nodes;
  await userEvent.click(screen.getByRole("button", { name: "Save pipeline" }));
  await screen.findByText(/Your draft is retained/);
  expect(useEditorStore.getState().nodes).toEqual(before);
  expect(useEditorStore.getState().pipelineId).toBeNull();
  expect(screen.getByRole("button", { name: "Save pipeline" })).toBeEnabled();
});
it("does not replace the graph with a malformed successful response", async () => {
  server.use(
    http.post(url, () =>
      HttpResponse.json({
        id,
        project_id: project,
        name: "Bad",
        revision: 1,
        definition: { schema_version: 99, nodes: [], edges: [] },
      }),
    ),
  );
  setup();
  await userEvent.click(screen.getByRole("button", { name: "Save pipeline" }));
  await screen.findByText(/unsupported pipeline response/);
  expect(useEditorStore.getState().nodes).toHaveLength(1);
  expect(useEditorStore.getState().draftName).toBe("Inspection");
});
it("ignores late save responses after switching projects", async () => {
  let replied = false;
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as Pick<
        SavedPipeline,
        "name" | "definition"
      >;
      await delay(100);
      replied = true;
      return HttpResponse.json({
        ...body,
        id,
        project_id: project,
        revision: 1,
      });
    }),
  );
  setup();
  await userEvent.click(screen.getByRole("button", { name: "Save pipeline" }));
  act(() =>
    useEditorStore
      .getState()
      .setProject("33333333-3333-4333-8333-333333333333"),
  );
  await waitFor(() => expect(replied).toBe(true));
  expect(useEditorStore.getState().nodes).toHaveLength(0);
  expect(useEditorStore.getState().pipelineId).toBeNull();
});
