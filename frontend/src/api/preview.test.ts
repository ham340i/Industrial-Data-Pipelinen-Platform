import { expect, it } from "vitest";
import { parsePreview, type PreviewRequest } from "./preview";
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
