import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { server } from "../test/server";
import { getProject, getProjects, parseProject } from "./projects";

const id = "9aba7db9-78b2-42d8-9320-68a675963eee";
it.each([
  null,
  {},
  { id: "bad", name: "x", created_at: "2026-10-14T10:00:00Z" },
  { id, name: "", created_at: "2026-10-14T10:00:00Z" },
  { id, name: "x", created_at: "not-a-date" },
])("rejects unsupported project JSON %j", (value) => {
  expect(() => parseProject(value)).toThrow();
});
it("rejects malformed pagination", async () => {
  server.use(
    http.get("http://127.0.0.1:8000/api/v1/projects", () =>
      HttpResponse.json({ items: [], total: -1, offset: 0, limit: 20 }),
    ),
  );
  await expect(getProjects(0)).rejects.toMatchObject({
    kind: "invalid-response",
  });
});
it("rejects the wrong project returned for a valid link", async () => {
  server.use(
    http.get(`http://127.0.0.1:8000/api/v1/projects/${id}`, () =>
      HttpResponse.json({
        id: "00000000-0000-0000-0000-000000000000",
        name: "Other",
        created_at: "2026-10-14T10:00:00Z",
      }),
    ),
  );
  await expect(getProject(id)).rejects.toMatchObject({
    kind: "invalid-response",
  });
});
