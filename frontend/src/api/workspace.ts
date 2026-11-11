import { api, ApiError } from "./client";

export interface WorkspaceStatus {
  root_path: string | null;
  source: "application" | "environment" | "unconfigured";
  ready: boolean;
  message: string;
}

async function requestWorkspace(
  root?: string | null,
): Promise<WorkspaceStatus> {
  const response =
    root === undefined
      ? await api.get<unknown>("/settings/workspace", {
          validateStatus: () => true,
        })
      : await api.put<unknown>(
          "/settings/workspace",
          { root_path: root },
          { validateStatus: () => true },
        );
  const value = response.data as
    (Partial<WorkspaceStatus> & { error?: { message?: unknown } }) | null;
  if (response.status >= 400) {
    throw new ApiError(
      typeof value?.error?.message === "string"
        ? value.error.message
        : "Workspace settings are unavailable. Try again.",
      "http",
      response.status,
    );
  }
  if (
    !value ||
    (value.root_path !== null && typeof value.root_path !== "string") ||
    !["application", "environment", "unconfigured"].includes(
      String(value.source),
    ) ||
    typeof value.ready !== "boolean" ||
    typeof value.message !== "string"
  ) {
    throw new ApiError(
      "The API returned invalid workspace settings.",
      "invalid-response",
    );
  }
  return value as WorkspaceStatus;
}
export const getWorkspace = () => requestWorkspace();
export const saveWorkspace = (root: string | null) => requestWorkspace(root);
