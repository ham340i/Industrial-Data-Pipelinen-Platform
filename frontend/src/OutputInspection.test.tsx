// AI contribution: 50% or more AI-generated
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { server } from "./test/server";
import type { RunDetail } from "./api/runs";
import { OutputInspection } from "./OutputInspection";
const run = {
  id: "11111111-1111-4111-8111-111111111111",
  pipeline_revision_id: "22222222-2222-4222-8222-222222222222",
  outputs: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      name: "result.parquet",
      artifact_ref: "result.parquet",
      row_count: 51,
    },
  ],
} as RunDetail;
const url = "http://127.0.0.1:8000/api/v1/artifacts/:id/query";
function page(offset = 0) {
  return {
    schema_version: 1,
    artifact_id: run.outputs[0].id,
    run_id: run.id,
    pipeline_revision_id: run.pipeline_revision_id,
    columns: ["label", "total"],
    rows: offset ? [[null, 0]] : [["A", 30]],
    offset,
    limit: 50,
    has_more: offset === 0,
  };
}
function setup() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const view = (value: RunDetail) => (
    <QueryClientProvider client={client}>
      <OutputInspection run={value} />
    </QueryClientProvider>
  );
  return { ...render(view(run)), view };
}
it("inspects and pages governed outputs, rendering nulls and zero", async () => {
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as { offset: number };
      return HttpResponse.json(page(body.offset));
    }),
  );
  setup();
  const user = userEvent.setup();
  await user.click(
    screen.getByRole("button", { name: "Inspect output result.parquet" }),
  );
  expect(
    await screen.findByRole("cell", { name: "30" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next output rows" }));
  expect(
    await screen.findByRole("cell", { name: "0" }),
  ).toBeVisible();
  expect(screen.getByRole("cell", { name: "null" })).toBeVisible();
  expect(
    screen.queryByRole("cell", { name: "A" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Next output rows" }),
  ).toBeDisabled();
});
it("keeps execution intact and retries unavailable rows without showing stale pages", async () => {
  let requests = 0;
  server.use(
    http.post(url, () =>
      ++requests === 1
        ? HttpResponse.json({}, { status: 409 })
        : HttpResponse.json(page()),
    ),
  );
  setup();
  const user = userEvent.setup();
  await user.click(
    screen.getByRole("button", { name: "Inspect output result.parquet" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("later run");
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry output rows" }));
  expect(await screen.findByRole("table")).toBeVisible();
  expect(requests).toBe(2);
});
it("clears the old table when switching run identity", async () => {
  server.use(http.post(url, () => HttpResponse.json(page())));
  const { rerender, view } = setup();
  await userEvent.click(
    screen.getByRole("button", { name: "Inspect output result.parquet" }),
  );
  const table = await screen.findByRole("table");
  expect(within(table).getByText("A")).toBeVisible();
  rerender(view({ ...run, id: "44444444-4444-4444-8444-444444444444" }));
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Inspect output result.parquet" }),
  ).toHaveAttribute("aria-expanded", "false");
});
