// AI contribution: 50% or more AI-generated
import { expect, it } from "vitest";
import { parseRun } from "./runs";
const detail = {
  schema_version: 1,
  id: "run",
  project_id: "project",
  pipeline_id: "pipeline",
  revision: 1,
  state: "failed",
  duration_ms: 0,
  row_count: 0,
  error: { code: "sql_query_failed", reason: "Read query failed." },
  blocks: [
    {
      node_id: "sql",
      state: "failed",
      duration_ms: 0,
      rows_in: null,
      rows_out: 0,
      error: { code: "sql_query_failed", reason: "Read query failed." },
    },
  ],
  events: [{ sequence: 1, message: "Block failed." }],
  outputs: [],
};
it("preserves measured zero, unknown counts, and structured failures", () => {
  expect(parseRun(detail, "project", "pipeline", "run")).toEqual(detail);
});
it.each([
  { project_id: "another" },
  { pipeline_id: "another" },
  { id: "another" },
  { row_count: -1 },
  { duration_ms: "0" },
  { blocks: [{}] },
  { events: [{}] },
  { outputs: [{}] },
  { error: { code: "broken" } },
  { state: "invented" },
])("rejects mismatched identities and malformed run data %j", (patch) => {
  expect(() =>
    parseRun({ ...detail, ...patch }, "project", "pipeline", "run"),
  ).toThrow("unsupported run response");
});
