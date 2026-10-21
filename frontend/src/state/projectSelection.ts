import { api } from "../api/client";
import { isProjectId } from "../api/projects";

// Only identity is durable in the browser; metadata stays in TanStack Query/SQLite.
const key = `lps.selected-project:${api.defaults.baseURL}`;
export function selectedProject(): string | null {
  try {
    const value = localStorage.getItem(key);
    return value && isProjectId(value) ? value : null;
  } catch {
    return null;
  }
}
export function rememberProject(id: string): void {
  if (!isProjectId(id)) return;
  try {
    localStorage.setItem(key, id);
  } catch {
    /* URL still preserves this session's selection. */
  }
}
export function forgetProject(id: string): void {
  try {
    if (localStorage.getItem(key) === id) localStorage.removeItem(key);
  } catch {
    /* Storage can be unavailable. */
  }
}
