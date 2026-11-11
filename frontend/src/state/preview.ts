import { normalizeApiError } from "../api/client";
import { useEffect, useRef, useState } from "react";
import {
  previewNode,
  type PreviewRequest,
  type PreviewResult,
} from "../api/preview";

export type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: PreviewResult }
  | { status: "error"; error: Error };

// Used as the session component's React key: semantic edits, project/draft,
// selection, output and limits discard results immediately, before effects run.
export function previewIdentity(
  projectId: string,
  generation: number,
  request: PreviewRequest,
  busy: boolean,
): string {
  return JSON.stringify([projectId, generation, request, busy]);
}

export function usePreview(projectId: string, request: PreviewRequest) {
  const [state, setState] = useState<PreviewState>({ status: "idle" });
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function refresh() {
    controller.current?.abort();
    const active = new AbortController();
    controller.current = active;
    setState({ status: "loading" });
    try {
      const result = await previewNode(projectId, request, active.signal);
      if (!active.signal.aborted && controller.current === active)
        setState({ status: "success", result });
    } catch (error) {
      if (!active.signal.aborted && controller.current === active)
        setState({
          status: "error",
          error: normalizeApiError(error),
        });
    }
  }
  function cancel() {
    controller.current?.abort();
    controller.current = null;
    setState({ status: "idle" });
  }
  return { state, refresh, cancel };
}
