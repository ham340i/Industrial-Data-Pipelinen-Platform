// AI contribution: 50% or more AI-generated
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { WorkspaceSettings } from "./WorkspaceSettings";
import { getWorkspace } from "./api/workspace";
import { server } from "./test/server";
import { useEditorStore } from "./state/editor";

const url = "http://127.0.0.1:8000/api/v1/settings/workspace";
const initial = {
  root_path: null,
  source: "unconfigured",
  ready: false,
  message: "Configure workspace",
  allowed_roots: ["/data/workspaces"],
};
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <WorkspaceSettings />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, client };
}
it("saves a validated path and restores environment configuration", async () => {
  useEditorStore.getState().setProject("project-id");
  const sent: unknown[] = [];
  server.use(
    http.get(url, () => HttpResponse.json(initial)),
    http.put(url, async ({ request }) => {
      const body = (await request.json()) as { root_path: string | null };
      sent.push(body);
      return HttpResponse.json({
        root_path: body.root_path ?? "/environment",
        source: body.root_path ? "application" : "environment",
        ready: true,
        message: "Ready",
        allowed_roots: initial.allowed_roots,
      });
    }),
  );
  mount();
  await waitFor(() =>
    expect(screen.getByLabelText("Workspace root folder")).toBeEnabled(),
  );
  await userEvent.type(
    screen.getByLabelText("Workspace root folder"),
    "/data/workspaces",
  );
  await userEvent.type(
    screen.getByLabelText("Workspace root folder"),
    "{Enter}",
  );
  expect(await screen.findByText(/Workspace saved/)).toBeVisible();
  expect(screen.getByLabelText("Workspace root folder")).toHaveValue(
    "/data/workspaces",
  );
  expect(sent).toEqual([{ root_path: "/data/workspaces" }]);
  await userEvent.click(
    screen.getByRole("button", { name: "Use environment setting" }),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Workspace root folder")).toHaveValue(
      "/environment",
    ),
  );
  expect(
    screen.queryByRole("link", { name: "Return to project builder" }),
  ).not.toBeInTheDocument();
});
it("keeps the entered path and current setting when validation fails", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json({
        ...initial,
        root_path: "/existing",
        source: "environment",
        ready: true,
      }),
    ),
    http.put(url, () =>
      HttpResponse.json(
        {
          error: {
            message: "Choose an existing folder the API can read and write.",
          },
        },
        { status: 422 },
      ),
    ),
  );
  mount();
  const field = screen.getByLabelText("Workspace root folder");
  await waitFor(() => expect(field).toHaveValue("/existing"));
  await userEvent.clear(field);
  await userEvent.type(field, "/missing");
  await userEvent.type(
    screen.getByLabelText("Workspace root folder"),
    "{Enter}",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Choose an existing folder",
  );
  expect(field).toHaveValue("/missing");
});
it("allows repairing settings after a load error", async () => {
  server.use(
    http.get(url, () =>
      HttpResponse.json(
        { error: { message: "Saved settings could not be read." } },
        { status: 503 },
      ),
    ),
  );
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Saved settings could not be read.",
  );
  expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  expect(screen.getByLabelText("Workspace root folder")).toBeEnabled();
});

it.each([undefined, "not-a-list", [123]])(
  "rejects malformed permitted roots %j",
  async (allowed_roots) => {
    server.use(
      http.get(url, () => HttpResponse.json({ ...initial, allowed_roots })),
    );
    await expect(getWorkspace()).rejects.toThrow("invalid workspace settings");
  },
);

it("autosaves a confirmed native folder and reloads the available projects", async () => {
  const sent: unknown[] = [];
  const pickerRequests: unknown[] = [];
  server.use(
    http.get(url, () => HttpResponse.json(initial)),
    http.post(`${url}/pick-folder`, async ({ request }) => {
      pickerRequests.push(await request.json());
      return HttpResponse.json({ path: "/data/New workspace" });
    }),
    http.put(url, async ({ request }) => {
      const body = (await request.json()) as { root_path: string };
      sent.push(body);
      return HttpResponse.json({
        ...initial,
        root_path: body.root_path,
        source: "application",
        ready: true,
      });
    }),
  );
  mount();
  const browse = screen.getByRole("button", { name: /Browse/ });
  await waitFor(() => expect(browse).toBeEnabled());
  await userEvent.click(browse);
  await waitFor(() =>
    expect(screen.getByLabelText("Workspace root folder")).toHaveValue(
      "/data/New workspace",
    ),
  );
  expect(pickerRequests).toEqual([{ initial_path: null }]);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Save workspace" }),
  ).not.toBeInTheDocument();
  await screen.findByText(/Workspace saved/);
  expect(sent).toEqual([{ root_path: "/data/New workspace" }]);
});

it("keeps an entered workspace path when the native picker is cancelled", async () => {
  server.use(
    http.get(url, () => HttpResponse.json(initial)),
    http.post(`${url}/pick-folder`, () => HttpResponse.json({ path: null })),
  );
  mount();
  const field = screen.getByLabelText("Workspace root folder");
  await waitFor(() => expect(field).toBeEnabled());
  await userEvent.type(field, "/data/typed");
  await userEvent.click(screen.getByRole("button", { name: /Browse/ }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Browse/ })).toBeEnabled(),
  );
  expect(field).toHaveValue("/data/typed");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("shows native-picker errors and keeps manual entry available", async () => {
  server.use(
    http.get(url, () => HttpResponse.json(initial)),
    http.post(`${url}/pick-folder`, () =>
      HttpResponse.json(
        { error: { message: "Enter a workspace folder path instead." } },
        { status: 409 },
      ),
    ),
  );
  mount();
  const browse = screen.getByRole("button", { name: /Browse/ });
  await waitFor(() => expect(browse).toBeEnabled());
  await userEvent.click(browse);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Enter a workspace folder path instead.",
  );
  expect(screen.getByLabelText("Workspace root folder")).toBeEnabled();
  expect(browse).toBeEnabled();
});

it("reloads each workspace's projects and pipelines and restores its unsaved draft", async () => {
  const firstProject = "11111111-1111-4111-8111-111111111111";
  const secondProject = "22222222-2222-4222-8222-222222222222";
  let active = "/first";
  const reads: string[] = [];
  useEditorStore.getState().switchWorkspace(active);
  useEditorStore.getState().setProject(firstProject);
  useEditorStore.getState().setDraftName("Unsaved first workspace draft");
  server.use(
    http.get(url, () =>
      HttpResponse.json({
        ...initial,
        root_path: active,
        source: "application",
        ready: true,
      }),
    ),
    http.post(`${url}/pick-folder`, () =>
      HttpResponse.json({ path: active === "/first" ? "/second" : "/first" }),
    ),
    http.put(url, async ({ request }) => {
      active = ((await request.json()) as { root_path: string }).root_path;
      return HttpResponse.json({
        ...initial,
        root_path: active,
        source: "application",
        ready: true,
      });
    }),
    http.get("http://127.0.0.1:8000/api/v1/projects/:id", ({ params }) =>
      params.id === (active === "/first" ? firstProject : secondProject)
        ? HttpResponse.json({
            id: params.id,
            name: active,
            created_at: "2026-11-17T00:00:00Z",
          })
        : new HttpResponse(null, { status: 404 }),
    ),
    http.get("http://127.0.0.1:8000/api/v1/projects", () => {
      reads.push(active);
      return HttpResponse.json({
        items: [
          {
            id: active === "/first" ? firstProject : secondProject,
            name: active,
            created_at: "2026-11-17T00:00:00Z",
          },
        ],
        total: 1,
        offset: 0,
        limit: 20,
      });
    }),
    http.get(
      `http://127.0.0.1:8000/api/v1/projects/${firstProject}/pipelines`,
      () => {
        reads.push("first pipelines");
        return HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 });
      },
    ),
  );
  const { client } = mount();
  await waitFor(() =>
    expect(screen.getByLabelText("Workspace root folder")).toHaveValue(
      "/first",
    ),
  );
  await userEvent.click(screen.getByRole("button", { name: /Browse/ }));
  await screen.findByText(/Workspace saved/);
  expect(useEditorStore.getState().projectId).toBeNull();
  expect(useEditorStore.getState().draftName).toBe("");
  expect(client.getQueryData(["projects", "/second", 0])).toMatchObject({
    items: [{ id: secondProject }],
  });
  await userEvent.click(screen.getByRole("button", { name: /Browse/ }));
  await waitFor(() =>
    expect(useEditorStore.getState().workspaceKey).toBe("/first"),
  );
  await waitFor(() => expect(reads).toContain("first pipelines"));
  expect(useEditorStore.getState().projectId).toBe(firstProject);
  expect(useEditorStore.getState().draftName).toBe(
    "Unsaved first workspace draft",
  );
  expect(reads).toContain("/first");
});

it("keeps the previous workspace active after an autosave failure and allows retry", async () => {
  let attempts = 0;
  server.use(
    http.get(url, () =>
      HttpResponse.json({
        ...initial,
        root_path: "/previous",
        source: "application",
        ready: true,
      }),
    ),
    http.post(`${url}/pick-folder`, () =>
      HttpResponse.json({ path: "/chosen" }),
    ),
    http.put(url, () =>
      ++attempts === 1
        ? HttpResponse.json(
            { error: { message: "Folder is unwritable." } },
            { status: 422 },
          )
        : HttpResponse.json({
            ...initial,
            root_path: "/chosen",
            source: "application",
            ready: true,
          }),
    ),
  );
  mount();
  await waitFor(() =>
    expect(screen.getByLabelText("Workspace root folder")).toHaveValue(
      "/previous",
    ),
  );
  await userEvent.click(screen.getByRole("button", { name: /Browse/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The previous workspace remains active",
  );
  expect(useEditorStore.getState().workspaceKey).toBe("/previous");
  expect(screen.getByLabelText("Workspace root folder")).toHaveValue("/chosen");
  await userEvent.click(screen.getByRole("button", { name: "Retry save" }));
  await screen.findByText(/Workspace saved/);
  expect(useEditorStore.getState().workspaceKey).toBe("/chosen");
  expect(attempts).toBe(2);
});
