// AI contribution: 50% or more AI-generated
import { expect, it } from "vitest";
import { ApiError } from "./client";
import { object } from "./guards";
import { parseDefinition } from "./pipelines";
import { parseProject } from "./projects";
import { parseRun } from "./runs";
import { parseReport } from "./validation";

it.each([null, [], "text", 1, undefined])("rejects non-record %j", (value) => {
  expect(object(value)).toBe(false);
});
it("accepts a response record", () => {
  expect(object({ schema_version: 1 })).toBe(true);
});
it.each([
  [() => parseDefinition(null), "pipeline response"],
  [() => parseProject(null), "project response"],
  [() => parseRun(null, "project", "pipeline", "run"), "run response"],
  [() => parseReport(null), "validation response"],
] as const)(
  "preserves endpoint-specific invalid response errors %#",
  (parse, text) => {
    let failure: unknown;
    try {
      parse();
    } catch (error) {
      failure = error;
    }
    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ kind: "invalid-response" });
    expect((failure as Error).message).toContain(text);
  },
);
