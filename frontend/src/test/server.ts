import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const healthUrl = "http://127.0.0.1:8000/health";
export const server = setupServer(
  http.get(healthUrl, () => HttpResponse.json({ status: "ok" })),
);
