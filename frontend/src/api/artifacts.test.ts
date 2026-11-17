// AI contribution: 50% or more AI-generated
import { expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/server";
import { queryArtifact } from "./artifacts";
const identity = {
  artifactId: "11111111-1111-4111-8111-111111111111",
  runId: "22222222-2222-4222-8222-222222222222",
  revisionId: "33333333-3333-4333-8333-333333333333",
};
const url = `http://127.0.0.1:8000/api/v1/artifacts/${identity.artifactId}/query`;
const page = {
  schema_version: 1,
  artifact_id: identity.artifactId,
  run_id: identity.runId,
  pipeline_revision_id: identity.revisionId,
  columns: ["label", "total"],
  rows: [
    ["A", 30],
    [null, 0],
  ],
  offset: 50,
  limit: 50,
  has_more: false,
};
it("queries a bounded governed page and preserves null and measured zero", async () => {
  server.use(
    http.post(url, async ({ request }) => {
      expect(await request.json()).toEqual({
        columns: [],
        offset: 50,
        limit: 50,
      });
      return HttpResponse.json(page);
    }),
  );
  expect(await queryArtifact(identity, 50)).toEqual(page);
});
it.each([
  { artifact_id: identity.runId },
  { run_id: identity.artifactId },
  { pipeline_revision_id: identity.runId },
  { offset: 0 },
  { limit: 500 },
  { columns: ["x", "x"] },
  { rows: [["ragged"]] },
  { rows: [[{}, 30]] },
  { has_more: "false" },
  { rows: Array.from({ length: 51 }, () => ["A", 30]) },
])("rejects mismatched or malformed evidence: %j", async (change) => {
  server.use(http.post(url, () => HttpResponse.json({ ...page, ...change })));
  await expect(queryArtifact(identity, 50)).rejects.toMatchObject({
    kind: "invalid-response",
  });
});
