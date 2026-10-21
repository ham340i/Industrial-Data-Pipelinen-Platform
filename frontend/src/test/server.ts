import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const healthUrl = "http://127.0.0.1:8000/api/v1/health";
export const server = setupServer(
  http.get("http://127.0.0.1:8000/api/v1/projects/:projectId/pipelines", () =>
    HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
  ),
  http.get("http://127.0.0.1:8000/api/v1/blocks", () => HttpResponse.json([])),
  http.post("http://127.0.0.1:8000/api/v1/pipelines/validate", () =>
    HttpResponse.json({ valid: true, diagnostics: [] }),
  ),
  http.get(healthUrl, () => HttpResponse.json({ status: "ok" })),
  http.get("http://127.0.0.1:8000/api/v1/projects", ({ request }) => {
    const offset = Number(new URL(request.url).searchParams.get("offset") || 0);
    return HttpResponse.json({ items: [], total: 0, offset, limit: 20 });
  }),
);
