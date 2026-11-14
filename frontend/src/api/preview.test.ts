import { expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/server";
import { parsePreview, previewNode, type PreviewRequest } from "./preview";
import { previewResult } from "../test/preview";

const request: PreviewRequest = {
  definition: { schema_version: 1, nodes: [], edges: [] },
  node_id: "csv",
  output_port: "table",
  limits: { max_rows: 20, max_cells: 2000 },
};
it.each([
  { node_id: "other" },
  { full_row_count: 200 },
  { full_count_scope: "observed" },
  { full_count_scope: "file_metadata", full_row_count: 1 },
  { full_count_scope: "observed", full_row_count: 200 },
  { full_count_scope: "file_metadata", full_row_count: 200, truncated: false },
  { sample_row_count: 100 },
  { null_scope: "whole_input" },
  { nulls: [{ column: "value", null_count: 2 }] },
  { effective_limits: { max_rows: 1000, max_cells: 10000 } },
  { rows: [{ value: [] }, { value: null }] },
])("rejects inconsistent or unsafe preview data %j", (change) => {
  expect(() =>
    parsePreview({ ...previewResult(request), ...change }, request),
  ).toThrow("invalid preview response");
});
it("accepts a bounded preview with explicitly unknown full count", () => {
  expect(
    parsePreview(previewResult(request), request).full_row_count,
  ).toBeNull();
});
it("accepts a truncated Parquet sample with a metadata-derived full count", () => {
  const value = {
    ...previewResult(request),
    schema_scope: "file_metadata",
    full_count_scope: "file_metadata",
    full_row_count: 200,
  };
  expect(parsePreview(value, request).full_row_count).toBe(200);
});
it("accepts a JSON schema explicitly scoped to its sample", () => {
  expect(
    parsePreview({ ...previewResult(request), schema_scope: "sample" }, request)
      .schema_scope,
  ).toBe("sample");
});

it.each(["csv", "missing"])(
  "binds error recovery to the request snapshot for %s",
  async (nodeId) => {
    const snapshot: PreviewRequest = {
      ...request,
      definition: {
        ...request.definition,
        nodes: [
          {
            id: "csv",
            block_id: "source.csv",
            block_version: "1.0.0",
            config: {},
          },
        ],
      },
    };
    server.use(
      http.post(
        "http://127.0.0.1:8000/api/v1/projects/project/pipelines/preview",
        () =>
          HttpResponse.json(
            {
              error: {
                code: "file_unavailable",
                message: "Private exception at /private/file.csv",
                node_context: nodeId,
                field: "resource_ref",
                port: "table",
                correlation_id: "trace-1",
              },
            },
            { status: 422 },
          ),
      ),
    );
    await expect(
      previewNode("project", snapshot, new AbortController().signal),
    ).rejects.toMatchObject({
      message: "Input file is missing or unreadable.",
      nodeId: nodeId === "csv" ? "csv" : null,
      field: nodeId === "csv" ? "resource_ref" : null,
    });
  },
);

it("does not display arbitrary message, field, port or reference details", async () => {
  server.use(
    http.post(
      "http://127.0.0.1:8000/api/v1/projects/project/pipelines/preview",
      () =>
        HttpResponse.json(
          {
            error: {
              code: "future_failure",
              message: "Private exception at /private/file.csv",
              node_context: "csv",
              field: "/private/field",
              port: "/private/port",
              correlation_id: "/private/trace",
            },
          },
          { status: 500 },
        ),
    ),
  );
  await expect(
    previewNode("project", request, new AbortController().signal),
  ).rejects.toMatchObject({
    message:
      "Preview could not complete. Check the input path and configuration, then retry. Your draft is unchanged.",
    nodeId: null,
    field: null,
    port: null,
    correlationId: "unavailable",
  });
});
