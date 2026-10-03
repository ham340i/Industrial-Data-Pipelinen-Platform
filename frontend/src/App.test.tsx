import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { server, healthUrl } from "./test/server";

function renderApp(route = "/") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("workbench", () => {
  it("shows loading before a successful health response", async () => {
    server.use(
      http.get(healthUrl, async () => {
        await delay(80);
        return HttpResponse.json({ status: "ok" });
      }),
    );
    renderApp();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking the local API",
    );
    expect(await screen.findByText("Local API is connected.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows a safe error and recovers with Retry", async () => {
    server.use(
      http.get(healthUrl, () =>
        HttpResponse.json({ secret: "PRIVATE_SERVER_DETAIL" }, { status: 503 }),
      ),
    );
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 503");
    expect(screen.queryByText(/PRIVATE_SERVER_DETAIL/)).not.toBeInTheDocument();
    server.use(http.get(healthUrl, () => HttpResponse.json({ status: "ok" })));
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Local API is connected.")).toBeVisible();
  });

  it("reports network failure without preventing navigation", async () => {
    server.use(http.get(healthUrl, () => HttpResponse.error()));
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot reach the local API",
    );
    await userEvent.click(screen.getByRole("link", { name: "Projects" }));
    expect(
      screen.getByRole("heading", { name: "Project storage is coming next" }),
    ).toBeVisible();
  });

  it("rejects incompatible health JSON", async () => {
    server.use(
      http.get(healthUrl, () => HttpResponse.json({ status: "unknown" })),
    );
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "unsupported health response",
    );
  });

  it("supports keyboard skip and route navigation with focus transfer", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.tab();
    expect(
      screen.getByRole("link", { name: "Skip to main content" }),
    ).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
    screen.getByRole("link", { name: "Projects" }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "Projects" })).toBeVisible();
    expect(screen.getByRole("main")).toHaveFocus();
    await waitFor(() =>
      expect(document.title).toBe("Projects | Local Pipeline Studio"),
    );
  });

  it("keeps a local draft across navigation and allows an explicit reset", async () => {
    const user = userEvent.setup();
    renderApp("/builder");
    await user.type(
      screen.getByRole("textbox", { name: "Draft pipeline name" }),
      "Synthetic inspection",
    );
    await user.click(screen.getByRole("link", { name: "Projects" }));
    await user.click(screen.getByRole("link", { name: "Builder" }));
    expect(screen.getByRole("textbox")).toHaveValue("Synthetic inspection");
    await user.click(screen.getByRole("button", { name: "Clear draft" }));
    expect(screen.getByRole("textbox")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Clear draft" })).toBeDisabled();
  });

  it("provides a recovery route for unknown URLs", async () => {
    renderApp("/missing");
    expect(
      screen.getByRole("heading", { name: "Page not found" }),
    ).toBeVisible();
    await userEvent.click(
      screen.getByRole("link", { name: "Return to overview" }),
    );
    expect(await screen.findByText("Local API is connected.")).toBeVisible();
  });
});
