// AI contribution: 50% or more AI-generated
import { api } from "../api/client";
import { isProjectId } from "../api/projects";
import { useEditorStore } from "./editor";

// Only identity is durable in the browser; metadata stays in TanStack Query/SQLite.
const selectionKey = () =>
  `lps.selected-project:${api.defaults.baseURL}:${useEditorStore.getState().workspaceKey ?? "unconfigured"}`;
export function selectedProject(): string | null {
  try {
    const value = localStorage.getItem(selectionKey());
    return value && isProjectId(value) ? value : null;
  } catch {
    return null;
  }
}
export function rememberProject(id: string): void {
  if (!isProjectId(id)) return;
  try {
    localStorage.setItem(selectionKey(), id);
  } catch {
    /* URL still preserves this session's selection. */
  }
}
export function forgetProject(id: string): void {
  try {
    const key = selectionKey();
    if (localStorage.getItem(key) === id) localStorage.removeItem(key);
  } catch {
    /* Storage can be unavailable. */
  }
}
