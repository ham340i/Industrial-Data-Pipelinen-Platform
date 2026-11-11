import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { WorkspaceSettings } from "./WorkspaceSettings";
import { server } from "./test/server";
import { useEditorStore } from "./state/editor";

const url = "http://127.0.0.1:8000/api/v1/settings/workspace";
const initial = {
  root_path: null,
  source: "unconfigured",
  ready: false,
  message: "Configure workspace",
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
it("saves a validated path, shows the project folder, and restores environment configuration", async () => {
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
      });
    }),
  );
  mount();
  await screen.findByText("No workspace root configured");
  await userEvent.type(
    screen.getByLabelText("Workspace root folder"),
    "/data/workspaces",
  );
  await userEvent.click(screen.getByRole("button", { name: "Save workspace" }));
  expect(await screen.findByText(/Workspace saved/)).toBeVisible();
  expect(screen.getByText(/Current project inputs:/)).toHaveTextContent(
    "/data/workspaces/project-id/inputs",
  );
  expect(sent).toEqual([{ root_path: "/data/workspaces" }]);
  await userEvent.click(
    screen.getByRole("button", { name: "Use environment setting" }),
  );
  expect(await screen.findByText("/environment")).toBeVisible();
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
  await screen.findByText("/existing");
  const field = screen.getByLabelText("Workspace root folder");
  await userEvent.clear(field);
  await userEvent.type(field, "/missing");
  await userEvent.click(screen.getByRole("button", { name: "Save workspace" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Choose an existing folder",
  );
  expect(field).toHaveValue("/missing");
  expect(screen.getByText("/existing")).toBeVisible();
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
