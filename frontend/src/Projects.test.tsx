import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { server } from "./test/server";
import { selectedProject, rememberProject } from "./state/projectSelection";

const url = "http://127.0.0.1:8000/api/v1/projects";
const project = {
  id: "9aba7db9-78b2-42d8-9320-68a675963eee",
  name: "Synthetic inspection",
  created_at: "2026-10-14T10:00:00Z",
};
function renderApp(route = "/projects") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const rendered = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...rendered, queryClient: client };
}
function detail() {
  server.use(
    http.get(`${url}/${project.id}`, () => HttpResponse.json(project)),
  );
}
describe("local projects", () => {
  it("clears a missing saved project even when old metadata is cached", async () => {
    detail();
    const { queryClient } = renderApp(`/projects/${project.id}/builder`);
    await screen.findByText("Project: Synthetic inspection");
    await waitFor(() => expect(selectedProject()).toBe(project.id));
    server.use(
      http.get(`${url}/${project.id}`, () =>
        HttpResponse.json({}, { status: 404 }),
      ),
    );
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ["project", project.id] });
    });
    expect(
      await screen.findByRole("heading", { name: "Project unavailable" }),
    ).toBeVisible();
    await waitFor(() => expect(selectedProject()).toBeNull());
  });
  it("paginates saved projects without losing access to the previous page", async () => {
    server.use(
      http.get(url, ({ request }) => {
        const offset = Number(new URL(request.url).searchParams.get("offset"));
        const items =
          offset === 0
            ? Array.from({ length: 20 }, (_, index) => ({
                ...project,
                id: `00000000-0000-0000-0000-${String(index).padStart(12, "0")}`,
                name: `Page one ${index}`,
              }))
            : [{ ...project, name: "Page two" }];
        return HttpResponse.json({ items, total: 21, offset, limit: 20 });
      }),
    );
    renderApp();
    await screen.findByRole("link", { name: "Open Page one 0" });
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(
      await screen.findByRole("link", { name: "Open Page two" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    await userEvent.click(
      screen.getByRole("button", { name: "Previous page" }),
    );
    expect(
      await screen.findByRole("link", { name: "Open Page one 0" }),
    ).toBeVisible();
  });
  it("loads, creates with trimmed name, and opens the confirmed workspace", async () => {
    server.use(
      http.get(url, async () => {
        await delay(50);
        return HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 });
      }),
    );
    const posted = vi.fn();
    server.use(
      http.post(url, async ({ request }) => {
        posted(await request.json());
        return HttpResponse.json(project, { status: 201 });
      }),
    );
    detail();
    renderApp();
    expect(screen.getByRole("status")).toHaveTextContent("Loading projects");
    expect(await screen.findByText(/No projects yet/)).toBeVisible();
    await userEvent.type(
      screen.getByRole("textbox", { name: "Project name" }),
      "  Synthetic inspection  ",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create project" }),
    );
    expect(
      await screen.findByText("Project: Synthetic inspection"),
    ).toBeVisible();
    expect(posted).toHaveBeenCalledWith({ name: "Synthetic inspection" });
    await waitFor(() => expect(selectedProject()).toBe(project.id));
    expect(
      screen.getByRole("heading", { name: "Pipeline builder" }),
    ).toBeVisible();
  });
  it("blocks blank names and retains the name after a creation failure", async () => {
    server.use(
      http.post(url, () =>
        HttpResponse.json({ detail: "PRIVATE" }, { status: 503 }),
      ),
    );
    renderApp();
    await userEvent.click(
      screen.getByRole("button", { name: "Create project" }),
    );
    expect(await screen.findByText(/Enter a name/)).toBeVisible();
    await userEvent.type(screen.getByRole("textbox"), "Synthetic inspection");
    await userEvent.click(
      screen.getByRole("button", { name: "Create project" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 503");
    expect(screen.getByRole("textbox")).toHaveValue("Synthetic inspection");
    expect(screen.queryByText("PRIVATE")).not.toBeInTheDocument();
  });
  it("recovers list failures through Retry", async () => {
    server.use(http.get(url, () => HttpResponse.error()));
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach");
    server.use(
      http.get(url, () =>
        HttpResponse.json({ items: [project], total: 1, offset: 0, limit: 20 }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("link", { name: "Open Synthetic inspection" }),
    ).toBeVisible();
  });
  it("opens a saved project using the keyboard and transfers focus", async () => {
    server.use(
      http.get(url, () =>
        HttpResponse.json({ items: [project], total: 1, offset: 0, limit: 20 }),
      ),
    );
    detail();
    renderApp();
    (
      await screen.findByRole("link", { name: "Open Synthetic inspection" })
    ).focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByText("Project: Synthetic inspection"),
    ).toBeVisible();
    expect(screen.getByRole("main")).toHaveFocus();
  });
  it("restores the last project through Builder after remount", async () => {
    rememberProject(project.id);
    detail();
    renderApp("/builder");
    expect(
      await screen.findByText("Project: Synthetic inspection"),
    ).toBeVisible();
  });
  it("clears missing saved IDs and provides recovery", async () => {
    rememberProject(project.id);
    server.use(
      http.get(`${url}/${project.id}`, () =>
        HttpResponse.json({}, { status: 404 }),
      ),
    );
    renderApp("/builder");
    expect(
      await screen.findByRole("heading", { name: "Project unavailable" }),
    ).toBeVisible();
    await waitFor(() => expect(selectedProject()).toBeNull());
    await userEvent.click(
      screen.getByRole("link", { name: "Choose a project" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Create a project" }),
    ).toBeVisible();
  });
  it("rejects malformed links without issuing a project request", async () => {
    renderApp("/projects/not-a-uuid/builder");
    expect(
      screen.getByRole("heading", { name: "Project unavailable" }),
    ).toBeVisible();
  });
  it("keeps drafts in the same project after Clear and navigation", async () => {
    detail();
    renderApp(`/projects/${project.id}/builder`);
    await screen.findByText("Project: Synthetic inspection");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Draft pipeline name" }),
      "First",
    );
    await userEvent.click(screen.getByRole("button", { name: "Clear draft" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Draft pipeline name" }),
      "Second",
    );
    await userEvent.click(screen.getByRole("link", { name: "Projects" }));
    await userEvent.click(screen.getByRole("link", { name: "Builder" }));
    expect(
      await screen.findByRole("textbox", { name: "Draft pipeline name" }),
    ).toHaveValue("Second");
  });
  it("keeps navigation usable when browser storage is blocked", async () => {
    const getter = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("blocked");
      });
    const setter = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("blocked");
      });
    detail();
    renderApp(`/projects/${project.id}/builder`);
    expect(
      await screen.findByText("Project: Synthetic inspection"),
    ).toBeVisible();
    getter.mockRestore();
    setter.mockRestore();
  });
});
