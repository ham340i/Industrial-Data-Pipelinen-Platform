import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { ConfigurationPanel } from "./configuration/ConfigurationPanel";
import { PreviewPanel } from "./PreviewPanel";
import type { PreviewRequest } from "./api/preview";
import { server } from "./test/server";
import { csvBlock, previewResult } from "./test/preview";
import { useEditorStore } from "./state/editor";

const url =
  "http://127.0.0.1:8000/api/v1/projects/:projectId/pipelines/preview";
function seed() {
  useEditorStore.getState().setProject("project");
  useEditorStore.getState().addBlock(csvBlock);
  useEditorStore.getState().addBlock(csvBlock);
  const nodes = useEditorStore.getState().nodes;
  useEditorStore.getState().selectNode(nodes[0].id);
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([
        {
          ...csvBlock,
          config_schema: {
            ...csvBlock.config_schema,
            additionalProperties: false,
          },
        },
      ]),
    ),
  );
  return nodes.map((n) => n.id);
}
function mount(projectId: string | null = "project") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const result = render(
    <QueryClientProvider client={client}>
      <PreviewPanel projectId={projectId} />
      <ConfigurationPanel />
    </QueryClientProvider>,
  );
  return { ...result, client };
}
const start = () =>
  screen.findByRole("button", { name: "Preview selected node" });

it.each(["sample", "file_metadata"] as const)(
  "labels %s provenance without claiming whole-input validation",
  async (scope) => {
    seed();
    server.use(
      http.post(url, async ({ request }) => {
        const result = previewResult((await request.json()) as PreviewRequest);
        result.schema_scope = scope;
        if (scope === "file_metadata") {
          result.full_count_scope = "file_metadata";
          result.full_row_count = 200;
        }
        return HttpResponse.json(result);
      }),
    );
    mount();
    await userEvent.click(await start());
    expect(await screen.findByText("sample-value")).toBeVisible();
    expect(
      screen.getByText(
        scope === "sample"
          ? /Schema inferred from sampled rows/
          : /Schema reported by file metadata/,
      ),
    ).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent(
      scope === "sample"
        ? "Full row count unknown"
        : "200 total rows reported by file metadata",
    );
  },
);

it("previews only on demand, displays scoped counts/schema/nulls and never caches rows", async () => {
  seed();
  const requests: PreviewRequest[] = [];
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as PreviewRequest;
      requests.push(body);
      return HttpResponse.json(previewResult(body));
    }),
  );
  const { client } = mount();
  const button = await start();
  expect(requests).toHaveLength(0);
  await userEvent.click(button);
  expect(await screen.findByText("sample-value")).toBeVisible();
  expect(screen.getByText(/Full row count unknown/)).toBeVisible();
  expect(requests[0].definition).not.toHaveProperty("layout");
  await userEvent.click(screen.getByRole("tab", { name: "Schema" }));
  expect(
    within(screen.getByRole("table", { name: "Preview schema" })).getByText(
      "string",
    ),
  ).toBeVisible();
  await userEvent.click(screen.getByRole("tab", { name: "Null summary" }));
  const nulls = within(screen.getByRole("table", { name: "Preview nulls" }));
  expect(nulls.getByText("1")).toBeVisible();
  expect(nulls.getByText("2")).toBeVisible();
  expect(
    JSON.stringify(
      client
        .getQueryCache()
        .getAll()
        .map((q) => q.state.data),
    ),
  ).not.toContain("sample-value");
  expect(JSON.stringify(useEditorStore.getState().nodes)).not.toContain(
    "sample-value",
  );
});

it("discards results on semantic edits, limits and selection, but keeps them on movement", async () => {
  const [a, b] = seed();
  let calls = 0;
  server.use(
    http.post(url, async ({ request }) => {
      calls++;
      return HttpResponse.json(
        previewResult((await request.json()) as PreviewRequest),
      );
    }),
  );
  mount();
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  act(() =>
    useEditorStore
      .getState()
      .changeNodes([{ type: "position", id: a, position: { x: 12, y: 34 } }]),
  );
  expect(screen.getByText("sample-value")).toBeVisible();
  act(() =>
    useEditorStore
      .getState()
      .setNodeConfiguration(a, { resource_ref: "changed.csv" }),
  );
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  expect(calls).toBe(1);
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  await userEvent.clear(
    screen.getByRole("spinbutton", { name: "Preview rows" }),
  );
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  expect(await start()).toBeDisabled();
  await userEvent.type(
    screen.getByRole("spinbutton", { name: "Preview rows" }),
    "5",
  );
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  act(() => useEditorStore.getState().selectNode(b));
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  act(() => useEditorStore.getState().selectNode(a));
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
});

it("ignores a late response after switching selection and supports cancellation", async () => {
  const [, b] = seed();
  let release!: () => void;
  let received = false;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as PreviewRequest;
      received = true;
      await pending;
      return HttpResponse.json(previewResult(body));
    }),
  );
  mount();
  await userEvent.click(await start());
  await waitFor(() => expect(received).toBe(true));
  expect(screen.getByText("Reading bounded preview…")).toBeVisible();
  act(() => useEditorStore.getState().selectNode(b));
  await act(async () => {
    release();
    await pending;
  });
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  let finish!: () => void;
  const blocked = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.post(url, async ({ request }) => {
      const body = (await request.json()) as PreviewRequest;
      await blocked;
      return HttpResponse.json(previewResult(body));
    }),
  );
  await userEvent.click(await start());
  await userEvent.click(screen.getByRole("button", { name: "Cancel preview" }));
  await act(async () => {
    finish();
    await blocked;
  });
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  expect(await start()).toBeEnabled();
});

it("clears successful data before a failed refresh and exposes safe field context", async () => {
  const [a] = seed();
  server.use(
    http.post(url, async ({ request }) =>
      HttpResponse.json(
        previewResult((await request.json()) as PreviewRequest),
      ),
    ),
  );
  mount();
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  server.use(
    http.post(url, () =>
      HttpResponse.json(
        {
          error: {
            code: "file_unavailable",
            message: "Input file is missing or unreadable.",
            node_context: a,
            field: "resource_ref",
            port: null,
            correlation_id: "preview-failure",
          },
        },
        { status: 422 },
      ),
    ),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Refresh preview" }),
  );
  expect(
    await screen.findByText("Input file is missing or unreadable."),
  ).toBeVisible();
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  expect(screen.getByText(/Reference: preview-failure/)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Configure node" }));
  expect(useEditorStore.getState().configFocus).toEqual({
    nodeId: a,
    field: "resource_ref",
  });
});

it("shows empty samples without losing their schema", async () => {
  seed();
  server.use(
    http.post(url, async ({ request }) =>
      HttpResponse.json({
        ...previewResult((await request.json()) as PreviewRequest),
        rows: [],
        sample_row_count: 0,
        sample_cell_count: 0,
        inspected_row_count: 0,
        full_row_count: 0,
        full_count_scope: "observed",
        truncated: false,
        nulls: [{ column: "value", null_count: 0 }],
      }),
    ),
  );
  mount();
  await userEvent.click(await start());
  expect(await screen.findByText(/No rows in this input/)).toBeVisible();
  await userEvent.click(screen.getByRole("tab", { name: "Schema" }));
  expect(screen.getByText("string")).toBeVisible();
});

it("discards results when output, project or draft generation changes", async () => {
  seed();
  const secondPort = { ...csvBlock.outputs[0], name: "alternate" };
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([
        { ...csvBlock, outputs: [...csvBlock.outputs, secondPort] },
      ]),
    ),
  );
  server.use(
    http.post(url, async ({ request }) =>
      HttpResponse.json(
        previewResult((await request.json()) as PreviewRequest),
      ),
    ),
  );
  const mounted = mount();
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Preview output" }),
    "alternate",
  );
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  mounted.rerender(
    <QueryClientProvider client={mounted.client}>
      <PreviewPanel projectId="another-project" />
    </QueryClientProvider>,
  );
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
  await userEvent.click(await start());
  await screen.findByText("sample-value");
  act(() => useEditorStore.setState((s) => ({ generation: s.generation + 1 })));
  expect(screen.queryByText("sample-value")).not.toBeInTheDocument();
});

it("explains unsupported blocks, no selection and missing project without requests", async () => {
  const [a] = seed();
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/blocks", () =>
      HttpResponse.json([
        {
          ...csvBlock,
          supports_preview: false,
          preview_reason: "No bounded reader is available.",
        },
      ]),
    ),
  );
  const mounted = mount();
  expect(
    await screen.findByText("No bounded reader is available."),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Preview selected node" }),
  ).not.toBeInTheDocument();
  act(() => useEditorStore.getState().selectNode(null));
  expect(
    screen.getByText("Select a node to preview its output."),
  ).toBeVisible();
  act(() => useEditorStore.getState().selectNode(a));
  mounted.rerender(
    <QueryClientProvider client={mounted.client}>
      <PreviewPanel projectId={null} />
    </QueryClientProvider>,
  );
  expect(
    screen.getByText("Open a project to preview its local data."),
  ).toBeVisible();
});

const failure = (node: string) =>
  HttpResponse.json(
    {
      error: {
        code: "file_unavailable",
        message: "Raw private exception /private/file.csv",
        node_context: node,
        field: "resource_ref",
        port: null,
        correlation_id: "safe-reference",
      },
    },
    { status: 422 },
  );

it("keyboard recovery focuses an upstream field without changing unsaved configuration", async () => {
  const [a, b] = seed();
  act(() =>
    useEditorStore
      .getState()
      .setNodeConfiguration(b, { resource_ref: "unsaved.csv" }),
  );
  act(() =>
    useEditorStore.setState({
      edges: [
        {
          id: "upstream",
          source: b,
          sourceHandle: "table",
          target: a,
          targetHandle: "table",
        },
      ],
    }),
  );
  const before = useEditorStore.getState().nodes.map((node) => node.data);
  const edgesBefore = useEditorStore.getState().edges;
  server.use(http.post(url, () => failure(b)));
  mount();
  await userEvent.click(await start());
  const configure = await screen.findByRole("button", {
    name: "Configure node",
  });
  expect(screen.queryByText(/Raw private exception/)).not.toBeInTheDocument();
  configure.focus();
  await userEvent.keyboard("{Enter}");
  await waitFor(() =>
    expect(document.activeElement).toHaveAttribute(
      "data-config-field",
      "resource_ref",
    ),
  );
  expect(useEditorStore.getState().selectedNodeId).toBe(b);
  expect(useEditorStore.getState().nodes.map((node) => node.data)).toEqual(
    before,
  );
  expect(useEditorStore.getState().edges).toEqual(edgesBefore);
  expect(a).not.toBe(b);
});

it("keeps unknown-node errors readable without a dead Configure action", async () => {
  seed();
  server.use(http.post(url, () => failure("absent-node")));
  mount();
  await userEvent.click(await start());
  expect(
    await screen.findByText("Input file is missing or unreadable."),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Configure node" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/Field:/)).not.toBeInTheDocument();
});

it("keeps keyboard focus meaningful through repeated retry, loading and cancel", async () => {
  const [a] = seed();
  server.use(http.post(url, () => failure(a)));
  mount();
  await userEvent.click(await start());
  const retry = await screen.findByRole("button", { name: "Retry preview" });
  const releases: (() => void)[] = [];
  server.use(
    http.post(url, async () => {
      await new Promise<void>((resolve) => releases.push(resolve));
      return failure(a);
    }),
  );
  retry.focus();
  await userEvent.keyboard("{Enter}{Enter}");
  await waitFor(() => expect(releases).toHaveLength(1));
  expect(
    screen.getByRole("button", { name: "Preview selected node" }),
  ).toHaveFocus();
  for (let i = 0; i < 3; i++) {
    await userEvent.tab();
    expect(
      screen.getByRole("button", { name: "Cancel preview" }),
    ).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(await start()).toHaveFocus();
    await userEvent.keyboard("{Enter}{Enter}");
    await waitFor(() => expect(releases).toHaveLength(i + 2));
  }
  await userEvent.tab();
  await act(async () => releases.forEach((release) => release()));
  expect(
    await screen.findByRole("button", { name: "Retry preview" }),
  ).toHaveFocus();
});

it.each(["selection", "edit", "project"])(
  "ignores a late failure after %s changes",
  async (change) => {
    const [a, b] = seed();
    let release!: () => void;
    let received = false;
    server.use(
      http.post(url, async () => {
        await new Promise<void>((resolve) => {
          release = resolve;
          received = true;
        });
        return failure(a);
      }),
    );
    const mounted = mount();
    await userEvent.click(await start());
    await waitFor(() => expect(received).toBe(true));
    if (change === "selection")
      act(() => useEditorStore.getState().selectNode(b));
    else if (change === "edit")
      act(() =>
        useEditorStore
          .getState()
          .setNodeConfiguration(a, { resource_ref: "new.csv" }),
      );
    else
      mounted.rerender(
        <QueryClientProvider client={mounted.client}>
          <PreviewPanel projectId="new-project" />
        </QueryClientProvider>,
      );
    await act(async () => release());
    expect(
      screen.queryByRole("button", { name: "Configure node" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Input file is missing or unreadable."),
    ).not.toBeInTheDocument();
    expect(await start()).toBeEnabled();
  },
);
it.each([false, true])(
  "completes a preview with meaningful focus without stealing it (moved away: %s)",
  async (moveAway) => {
    seed();
    let release!: () => void;
    let received = false;
    server.use(
      http.post(url, async ({ request }) => {
        const body = (await request.json()) as PreviewRequest;
        await new Promise<void>((resolve) => {
          release = resolve;
          received = true;
        });
        return HttpResponse.json(previewResult(body));
      }),
    );
    mount();
    const button = await start();
    button.focus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(received).toBe(true));
    await userEvent.tab();
    expect(
      screen.getByRole("button", { name: "Cancel preview" }),
    ).toHaveFocus();
    if (moveAway) {
      await userEvent.tab();
      expect(
        screen.getByRole("textbox", { name: "resource_ref" }),
      ).toHaveFocus();
    }
    const previousFocus = document.activeElement;
    await act(async () => release());
    expect(await screen.findByText("sample-value")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Full row count unknown",
    );
    expect(
      screen.queryByRole("button", { name: "Cancel preview" }),
    ).not.toBeInTheDocument();
    if (moveAway) expect(previousFocus).toHaveFocus();
    else
      expect(
        screen.getByRole("button", { name: "Refresh preview" }),
      ).toHaveFocus();
  },
);
