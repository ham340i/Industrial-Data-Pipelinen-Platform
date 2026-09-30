import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "./client";

export interface HealthResponse {
  status: "ok";
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const { data } = await api.get<unknown>("/health", { signal });
  if (
    typeof data !== "object" ||
    data === null ||
    !("status" in data) ||
    data.status !== "ok"
  ) {
    throw new ApiError(
      "The local API returned an unsupported health response. Check API compatibility.",
      "invalid-response",
    );
  }
  return { status: "ok" };
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    staleTime: 30000,
    retry: false,
    refetchOnWindowFocus: false,
  });
}
