import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "./client";

export interface Project {
  id: string;
  name: string;
  created_at: string;
}
export interface ProjectPage {
  items: Project[];
  total: number;
  offset: number;
  limit: number;
}
export const isProjectId = (value: string): boolean =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);

function invalid(): never {
  throw new ApiError(
    "The local API returned an unsupported project response.",
    "invalid-response",
  );
}
export function parseProject(value: unknown): Project {
  if (typeof value !== "object" || value === null) return invalid();
  const project = value as Record<string, unknown>;
  if (
    typeof project.id !== "string" ||
    !isProjectId(project.id) ||
    typeof project.name !== "string" ||
    !project.name.trim() ||
    typeof project.created_at !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(project.created_at) ||
    !Number.isFinite(Date.parse(project.created_at))
  )
    return invalid();
  return { id: project.id, name: project.name, created_at: project.created_at };
}
export async function getProjects(
  offset: number,
  signal?: AbortSignal,
): Promise<ProjectPage> {
  const { data } = await api.get<unknown>("/projects", {
    params: { offset, limit: 20 },
    signal,
  });
  if (typeof data !== "object" || data === null) return invalid();
  const page = data as Record<string, unknown>;
  if (
    !Array.isArray(page.items) ||
    !Number.isSafeInteger(page.total) ||
    typeof page.total !== "number" ||
    page.total < 0 ||
    page.offset !== offset ||
    page.limit !== 20 ||
    page.items.length > 20 ||
    page.items.length > page.total
  )
    return invalid();
  const items = page.items.map(parseProject);
  if (new Set(items.map((item) => item.id)).size !== items.length)
    return invalid();
  return { items, total: page.total, offset, limit: 20 };
}
export async function createProject(name: string): Promise<Project> {
  const { data } = await api.post<unknown>("/projects", { name });
  return parseProject(data);
}
export async function getProject(
  id: string,
  signal?: AbortSignal,
): Promise<Project> {
  if (!isProjectId(id))
    throw new ApiError("This project link is invalid.", "invalid-response");
  const { data } = await api.get<unknown>(`/projects/${id}`, { signal });
  const project = parseProject(data);
  if (project.id.toLowerCase() !== id.toLowerCase()) return invalid();
  return project;
}
export function useProject(id: string) {
  return useQuery({
    queryKey: ["project", id],
    queryFn: ({ signal }) => getProject(id, signal),
    enabled: isProjectId(id),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
