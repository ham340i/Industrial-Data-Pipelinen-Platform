import axios from "axios";

export type ApiErrorKind =
  "network" | "timeout" | "http" | "invalid-response" | "unknown";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly kind: ApiErrorKind,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      return new ApiError(
        "The local API took too long to respond. Try again.",
        "timeout",
      );
    }
    if (error.response) {
      return new ApiError(
        `The local API returned an error (HTTP ${error.response.status}). Try again.`,
        "http",
        error.response.status,
      );
    }
    return new ApiError(
      "Cannot reach the local API. Check that it is running and allows this workbench origin.",
      "network",
    );
  }
  return new ApiError(
    "An unexpected request error occurred. Try again.",
    "unknown",
  );
}

export function resolveApiBaseUrl(value: string | undefined): string {
  if (value?.trim() === "/api/v1") return "/api/v1";
  const input = value?.trim() || "http://127.0.0.1:8000/api/v1";
  const url = new URL(input);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "VITE_API_BASE_URL must be an HTTP(S) URL without credentials, query or fragment.",
    );
  }
  if (url.pathname === "/") url.pathname = "/api/v1";
  return url.href.replace(/\/$/, "");
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
  timeout: 10000,
  headers: { Accept: "application/json" },
  withCredentials: false,
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) =>
    Promise.reject(axios.isCancel(error) ? error : normalizeApiError(error)),
);
