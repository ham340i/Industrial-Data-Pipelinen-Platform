// AI contribution: 50% or more AI-generated
import { expect, it } from "vitest";
import { parseRun } from "./runs";
const detail = {
  schema_version: 1,
  id: "33333333-3333-4333-8333-333333333333",
  project_id: "project",
  pipeline_id: "pipeline",
  pipeline_revision_id: "22222222-2222-4222-8222-222222222222",
  created_at: "2026-11-10T12:00:00Z",
  started_at: null,
  ended_at: null,
  revision: 1,
  state: "failed",
  duration_ms: 0,
  row_count: 0,
  error: { code: "sql_query_failed", reason: "Read query failed." },
  blocks: [
    {
      node_id: "sql",
      position: 0,
      block_id: "source.sql",
      block_version: "1.0.0",
      started_at: null,
      ended_at: null,
      state: "failed",
      duration_ms: 0,
      rows_in: null,
      rows_out: 0,
      error: { code: "sql_query_failed", reason: "Read query failed." },
    },
  ],
  events: [
    {
      sequence: 1,
      message: "Block failed.",
      created_at: "2026-11-10T12:00:00Z",
      level: "error",
      node_id: "sql",
      kind: "block_failed",
      code: null,
    },
  ],
  outputs: [],
};
it("preserves measured zero, unknown counts, and structured failures", () => {
  expect(
    parseRun(
      detail,
      "project",
      "pipeline",
      "33333333-3333-4333-8333-333333333333",
    ),
  ).toEqual(detail);
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
    parseRun(
      { ...detail, ...patch },
      "project",
      "pipeline",
      "33333333-3333-4333-8333-333333333333",
    ),
  ).toThrow("unsupported or mismatched run evidence");
});
