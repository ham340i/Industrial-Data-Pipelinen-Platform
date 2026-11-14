// AI contribution: 50% or more AI-generated
// Shared response fixtures captured from the real backend by
// tests/test_integration_contracts.py (#37). If the backend changes a
// response shape, the Python side regenerates these files and this test
// proves the Builder's parsers still accept them.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";
import { parseRun } from "./runs";
import { parseReport } from "./validation";

// Resolved with node:path on purpose: a `new URL(..., import.meta.url)`
// literal is rewritten by Vite into an asset import, which it refuses to
// serve from outside the frontend package.
const contracts = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../tests/fixtures/contracts",
);
const fixture = (name: string): unknown =>
  JSON.parse(readFileSync(resolve(contracts, `${name}.json`), "utf-8"));
const run = (name: string) => {
  const data = fixture(name) as Record<string, string>;
  return parseRun(data, data.project_id, data.pipeline_id, data.id);
};

it("accepts a succeeded run recorded by the real API", () => {
  const detail = run("run-detail-succeeded");
  expect(detail.state).toBe("succeeded");
  expect(detail.error).toBeNull();
  expect(detail.blocks.map((b) => b.state)).toEqual([
    "completed",
    "completed",
    "completed",
  ]);
  expect(detail.outputs).toHaveLength(1);
  expect(detail.outputs[0].artifact_ref).toBe("outputs/result.parquet");
  expect(detail.row_count).toBe(3);
});

it("accepts a failed run with block-level and run-level errors", () => {
  const detail = run("run-detail-failed");
  expect(detail.state).toBe("failed");
  expect(detail.error?.code).toBe("quality_failed");
  expect(detail.blocks.map((b) => b.state)).toEqual([
    "completed",
    "failed",
    "skipped",
  ]);
  expect(detail.blocks[1].error?.code).toBe("quality_failed");
  expect(detail.outputs).toEqual([]);
});

it("accepts the validation report the API returns for a broken draft", () => {
  const report = parseReport(fixture("validation-report"));
  expect(report.valid).toBe(false);
  const codes = report.diagnostics.map((d) => d.code);
  expect(codes).toEqual(
    expect.arrayContaining([
      "block_unavailable",
      "missing_config",
      "incompatible_ports",
      "missing_input",
    ]),
  );
  expect(
    report.diagnostics.find((d) => d.code === "missing_config"),
  ).toMatchObject({ node_id: "csv", field: "resource_ref" });
});

it("rejects a mismatched project identity on the recorded run", () => {
  const data = fixture("run-detail-succeeded") as Record<string, string>;
  expect(() =>
    parseRun(data, data.pipeline_id, data.project_id, data.id),
  ).toThrow("run evidence");
});

it.each([
  [
    "a same-type event level the parser does not know",
    (d: Record<string, unknown>) => {
      (d.events as Record<string, unknown>[])[0].level = "warn";
    },
  ],
  [
    "a same-type block state the parser does not know",
    (d: Record<string, unknown>) => {
      (d.blocks as Record<string, unknown>[])[0].state = "done";
    },
  ],
  [
    "a repeated event sequence",
    (d: Record<string, unknown>) => {
      const events = d.events as Record<string, unknown>[];
      events[1].sequence = events[0].sequence;
    },
  ],
])("rejects the recorded run after %s", (_label, mutate) => {
  const data = fixture("run-detail-succeeded") as Record<string, unknown>;
  mutate(data);
  const ids = data as Record<string, string>;
  expect(() => parseRun(data, ids.project_id, ids.pipeline_id, ids.id)).toThrow(
    "run evidence",
  );
});

it("rejects a validation report whose valid flag contradicts its list", () => {
  const data = fixture("validation-report") as Record<string, unknown>;
  data.valid = true;
  expect(() => parseReport(data)).toThrow("validation response");
});
