// AI contribution: 50% or more AI-generated
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Stack, Typography } from "@mui/material";
import {
  executePipeline,
  ExecutionRequestError,
  getRun,
  isActiveRun,
} from "./api/runs";
import { normalizeApiError, type ApiError } from "./api/client";
import { fingerprint, useEditorStore } from "./state/editor";
import { semanticDefinition } from "./state/validation";

type Editor = ReturnType<typeof useEditorStore.getState>;
interface Attempt {
  projectId: string;
  pipelineId: string;
  generation: number;
  revision: number;
  semantic: string;
  pending: boolean;
  runId?: string;
  error?: ApiError;
}
const semantic = (state: Editor) =>
  JSON.stringify(semanticDefinition(state.nodes, state.edges));
const sameContext = (attempt: Attempt, state: Editor) =>
  attempt.projectId === state.projectId &&
  attempt.pipelineId === state.pipelineId &&
  attempt.generation === state.generation;
const sameDraft = (attempt: Attempt, state: Editor, revision: number) =>
  sameContext(attempt, state) &&
  attempt.revision === revision &&
  state.revision === revision &&
  attempt.semantic === semantic(state);

export function RunControls({ canRun }: { canRun: boolean }) {
  const state = useEditorStore();
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const requestNumber = useRef(0);
  const statusRef = useRef<HTMLParagraphElement>(null);
  const queryClient = useQueryClient();
  const visible = attempt && sameContext(attempt, state) ? attempt : null;
  const { projectId, pipelineId } = state;
  const dirty =
    state.savedFingerprint !==
    fingerprint(state.draftName, state.nodes, state.edges);
  const detail = useQuery({
    queryKey: ["run", projectId, pipelineId, visible?.runId],
    queryFn: ({ signal }) =>
      getRun(projectId!, pipelineId!, visible!.runId!, signal),
    enabled: Boolean(visible?.runId),
    retry: false,
    gcTime: 0,
    refetchInterval: ({ state: { data } }) =>
      data && isActiveRun(data.state) ? 1000 : false,
  });
  const result = visible?.runId ? detail.data : undefined;
  const matches = Boolean(
    result && visible && sameDraft(visible, state, result.revision),
  );
  function configure(nodeId: string, revision: number) {
    const now = useEditorStore.getState();
    if (
      visible &&
      !now.busy &&
      sameDraft(visible, now, revision) &&
      now.nodes.some((n) => n.id === nodeId)
    )
      now.focusConfiguration(nodeId, null);
  }
  async function run() {
    const start = useEditorStore.getState();
    if (
      !start.projectId ||
      !start.pipelineId ||
      !start.revision ||
      start.busy ||
      !canRun ||
      start.savedFingerprint !==
        fingerprint(start.draftName, start.nodes, start.edges)
    )
      return;
    const next: Attempt = {
      projectId: start.projectId,
      pipelineId: start.pipelineId,
      generation: start.generation,
      revision: start.revision,
      semantic: semantic(start),
      pending: true,
    };
    const number = ++requestNumber.current;
    const current = () =>
      number === requestNumber.current &&
      sameContext(next, useEditorStore.getState());
    statusRef.current?.focus();
    start.setBusy(true);
    setAttempt(next);
    try {
      const runId = await executePipeline(
        next.projectId,
        next.pipelineId,
        next.revision,
      );
      if (current()) setAttempt({ ...next, pending: false, runId });
    } catch (error) {
      if (current()) {
        setAttempt({
          ...next,
          pending: false,
          error: normalizeApiError(error),
        });
        if (error instanceof ExecutionRequestError && error.status === 422)
          void queryClient.invalidateQueries({ queryKey: ["validation"] });
      }
    } finally {
      if (current()) useEditorStore.getState().setBusy(false);
    }
  }
  const error = visible?.error;
  const blockedNode =
    error instanceof ExecutionRequestError &&
    error.nodeId &&
    visible &&
    sameDraft(visible, state, visible.revision) &&
    state.nodes.some((n) => n.id === error.nodeId)
      ? error.nodeId
      : null;
  const status = visible?.pending
    ? "Starting saved pipeline."
    : result
      ? `Run ${result.state} · revision ${result.revision}`
      : visible?.runId
        ? detail.isPending
          ? "Loading run results."
          : "Run results could not be loaded."
        : error
          ? "Execution request failed."
          : "No run requested.";
  return (
    <Stack spacing={2} aria-label="Pipeline execution">
      <Button
        variant="contained"
        disabled={
          state.busy || dirty || !pipelineId || !state.revision || !canRun
        }
        onClick={() => void run()}
      >
        Run saved pipeline
      </Button>
      {(dirty || !pipelineId) && (
        <Typography>Save the current graph before running.</Typography>
      )}
      <Typography
        ref={statusRef}
        tabIndex={-1}
        role="status"
        aria-label="Execution status"
      >
        {status}
      </Typography>
      {error && (
        <Alert
          severity="error"
          action={
            blockedNode ? (
              <Button
                disabled={state.busy}
                onClick={() => configure(blockedNode, visible!.revision)}
              >
                Configure blocked node {blockedNode}
              </Button>
            ) : undefined
          }
        >
          {error.kind === "timeout"
            ? "The local API took too long to confirm execution."
            : error.message}{" "}
          Your saved pipeline is retained.
          {!(error instanceof ExecutionRequestError) && (
            <Typography>
              The request may have started a run. Check run history before
              starting another execution.
            </Typography>
          )}
        </Alert>
      )}
      {visible?.runId && detail.isError && (
        <Alert
          severity="error"
          action={
            <Button
              onClick={() => {
                statusRef.current?.focus();
                void detail.refetch();
              }}
            >
              Retry run results
            </Button>
          }
        >
          {normalizeApiError(detail.error).message} Retrying results does not
          start another run. {result && "Showing the last loaded run results."}
        </Alert>
      )}
      {result && (
        <Stack spacing={1}>
          {!matches && (
            <Alert severity="info">
              These results belong to a different saved revision or draft. Your
              current edits are unchanged; configuration links are disabled.
            </Alert>
          )}
          <Typography>
            Duration: {result.duration_ms ?? "unknown"} ms · Output rows:{" "}
            {result.row_count ?? "unknown"}
          </Typography>
          {result.error && (
            <Alert severity="error">
              {result.error.code}: {result.error.reason}
            </Alert>
          )}
          {result.blocks.map((b) => (
            <Stack key={b.node_id} spacing={1}>
              <Typography>
                {b.node_id}: {b.state} · {b.duration_ms ?? "unknown"} ms · rows{" "}
                {b.rows_in ?? "unknown"} → {b.rows_out ?? "unknown"}
                {b.error ? ` · ${b.error.code}: ${b.error.reason}` : ""}
              </Typography>
              {(b.state === "failed" || b.error) &&
                matches &&
                state.nodes.some((n) => n.id === b.node_id) && (
                  <Button
                    sx={{ alignSelf: "flex-start" }}
                    disabled={state.busy}
                    onClick={() => configure(b.node_id, result.revision)}
                  >
                    Configure failed block {b.node_id}
                  </Button>
                )}
            </Stack>
          ))}
          <Typography component="h2" variant="h2">
            Run log
          </Typography>
          {result.events.map((e) => (
            <Typography key={e.sequence}>{e.message}</Typography>
          ))}
          <Typography component="h2" variant="h2">
            Output artifacts
          </Typography>
          {result.outputs.length === 0 && (
            <Typography>
              No indexed artifacts are available for this run.
            </Typography>
          )}
          {result.outputs.map((o) => (
            <Typography key={o.id}>
              {o.name} · {o.row_count ?? "unknown"} rows · {o.artifact_ref}
            </Typography>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
