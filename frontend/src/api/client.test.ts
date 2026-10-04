import axios, { AxiosError, CanceledError } from "axios";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { api, ApiError, normalizeApiError, resolveApiBaseUrl } from "./client";
import { getHealth } from "./health";
import { server, healthUrl } from "../test/server";

describe("API boundary", () => {
  it("normalizes timeouts and unknown errors without exposing details", () => {
    expect(
      normalizeApiError(new AxiosError("sensitive", "ECONNABORTED")).kind,
    ).toBe("timeout");
    expect(normalizeApiError(new Error("sensitive")).message).not.toContain(
      "sensitive",
    );
    const known = new ApiError("safe", "invalid-response");
    expect(normalizeApiError(known)).toBe(known);
  });
  it("normalizes an actual request timeout", async () => {
    server.use(
      http.get(healthUrl, async () => {
        await delay(100);
        return HttpResponse.json({ status: "ok" });
      }),
    );
    await expect(
      api.get("/health", { timeout: 10, adapter: "fetch" }),
    ).rejects.toMatchObject({
      kind: "timeout",
    });
  });
  it("keeps cancellation recognizable", async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(getHealth(controller.signal)).rejects.toBeInstanceOf(
      CanceledError,
    );
    expect(axios.isCancel(new CanceledError())).toBe(true);
  });
  it.each([null, [], "ok", { status: 1 }, {}])(
    "rejects malformed health payload %j",
    async (payload) => {
      server.use(http.get(healthUrl, () => HttpResponse.json(payload)));
      await expect(getHealth()).rejects.toMatchObject({
        kind: "invalid-response",
      });
    },
  );
  it("accepts additive fields but returns only the typed contract", async () => {
    server.use(
      http.get(healthUrl, () =>
        HttpResponse.json({ status: "ok", private: "not propagated" }),
      ),
    );
    await expect(getHealth()).resolves.toEqual({ status: "ok" });
  });
  it("validates public API configuration", () => {
    expect(resolveApiBaseUrl("/api/v1")).toBe("/api/v1");
    expect(resolveApiBaseUrl(undefined)).toBe("http://127.0.0.1:8000");
    expect(resolveApiBaseUrl("https://example.test/api/")).toBe(
      "https://example.test/api",
    );
    for (const value of [
      "ftp://example.test",
      "http://user:secret@example.test",
      "http://example.test?token=x",
      "http://example.test#x",
      "invalid",
    ]) {
      expect(() => resolveApiBaseUrl(value)).toThrow();
    }
  });
});
