// AI contribution: 50% or more AI-generated
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Stack, Typography } from "@mui/material";
import { executePipeline, getRun } from "./api/runs";
import { fingerprint, useEditorStore } from "./state/editor";

export function RunControls({ canRun }: { canRun: boolean }) {
  const state = useEditorStore();
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { projectId, pipelineId } = state;
  const dirty =
    state.savedFingerprint !==
    fingerprint(state.draftName, state.nodes, state.edges);
  const detail = useQuery({
    queryKey: ["run", projectId, pipelineId, runId],
    queryFn: ({ signal }) => getRun(projectId!, pipelineId!, runId!, signal),
    enabled: Boolean(projectId && pipelineId && runId),
    retry: false,
    refetchInterval: (query) =>
      ["queued", "running"].includes(query.state.data?.state ?? "")
        ? 1000
        : false,
  });
  async function run() {
    const start = useEditorStore.getState();
    if (!projectId || !pipelineId || start.busy || dirty || !canRun) return;
    start.setBusy(true);
    setRunId(null);
    setError(null);
    const current = () =>
      useEditorStore.getState().generation === start.generation &&
      useEditorStore.getState().projectId === projectId;
    try {
      const id = await executePipeline(projectId, pipelineId);
      if (current()) setRunId(id);
    } catch (e) {
      if (current())
        setError(
          e instanceof Error
            ? e.message
            : "Execution request failed. Try again.",
        );
    } finally {
      if (current()) useEditorStore.getState().setBusy(false);
    }
  }
  return (
    <Stack spacing={2} aria-label="Pipeline execution">
      <Button
        variant="contained"
        disabled={state.busy || dirty || !pipelineId || !canRun}
        onClick={() => void run()}
      >
        Run saved pipeline
      </Button>
      {(dirty || !pipelineId) && (
        <Typography>Save the current graph before running.</Typography>
      )}
      {error && (
        <Alert severity="error">{error} Your saved pipeline is retained.</Alert>
      )}
      {runId && detail.isPending && (
        <Typography role="status">Loading run results…</Typography>
      )}
      {detail.isError && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => void detail.refetch()}>
              Retry run results
            </Button>
          }
        >
          {detail.error.message}
        </Alert>
      )}
      {detail.data && (
        <Stack spacing={1}>
          <Typography role="status">
            Run {detail.data.state} · revision {detail.data.revision}
          </Typography>
          <Typography>
            Duration: {detail.data.duration_ms ?? "unknown"} ms · Output rows:{" "}
            {detail.data.row_count ?? "unknown"}
          </Typography>
          {detail.data.error && (
            <Alert severity="error">
              {detail.data.error.code}: {detail.data.error.reason}
            </Alert>
          )}
          {detail.data.blocks.map((b) => (
            <Typography key={b.node_id}>
              {b.node_id}: {b.state} · {b.duration_ms ?? "unknown"} ms · rows{" "}
              {b.rows_in ?? "unknown"} → {b.rows_out ?? "unknown"}
              {b.error ? ` · ${b.error.code}: ${b.error.reason}` : ""}
            </Typography>
          ))}
          <Typography component="h2" variant="h2">
            Run log
          </Typography>
          {detail.data.events.map((e) => (
            <Typography key={e.sequence}>{e.message}</Typography>
          ))}
          <Typography component="h2" variant="h2">
            Output artifacts
          </Typography>
          {detail.data.outputs.length === 0 && (
            <Typography>
              No indexed artifacts are available for this run.
            </Typography>
          )}
          {detail.data.outputs.map((o) => (
            <Typography key={o.id}>
              {o.name} · {o.row_count ?? "unknown"} rows · {o.artifact_ref}
            </Typography>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
