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
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <WorkspaceSettings />
      </MemoryRouter>
    </QueryClientProvider>,
  );
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
  expect(screen.getByText("Permitted folder: /data/workspaces")).toBeVisible();
  await userEvent.type(
    screen.getByLabelText("Workspace root folder"),
    "/data/workspaces",
  );
  await userEvent.click(screen.getByRole("button", { name: "Save workspace" }));
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
    screen.getByRole("link", { name: "Return to project builder" }),
  ).toHaveAttribute("href", "/projects/project-id/builder");
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
  await userEvent.click(screen.getByRole("button", { name: "Save workspace" }));
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

it("opens the native picker and saves the returned path only when Save is clicked", async () => {
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
  expect(sent).toEqual([]);
  await userEvent.click(screen.getByRole("button", { name: "Save workspace" }));
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
