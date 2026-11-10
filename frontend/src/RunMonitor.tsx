import { useState, useSyncExternalStore } from "react";
import { onlineManager, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { getRun, isActiveRun, listRuns, type RunDetail } from "./api/runs";
import { useEditorStore } from "./state/editor";

const label = (state: string) =>
  state === "succeeded" ? "Completed" : state[0].toUpperCase() + state.slice(1);
const measured = (value: number | null, unit = "") =>
  value === null ? "Unknown" : `${value.toLocaleString()}${unit}`;

function InspectNode({ id }: { id: string }) {
  const exists = useEditorStore((s) => s.nodes.some((n) => n.id === id));
  const busy = useEditorStore((s) => s.busy);
  return exists ? (
    <Button
      disabled={busy}
      onClick={() => useEditorStore.getState().focusConfiguration(id, null)}
    >
      Inspect {id}
    </Button>
  ) : (
    <Typography variant="caption">
      Node {id} is absent from this draft.
    </Typography>
  );
}
function Evidence({ run }: { run: RunDetail }) {
  const revision = useEditorStore((s) => s.revision);
  return (
    <Stack spacing={2} sx={{ overflowWrap: "anywhere", minWidth: 0 }}>
      <Typography role="status">
        {label(run.state)} · Run {run.id}
      </Typography>
      <Typography>
        Saved revision {run.revision} · Duration:{" "}
        {measured(run.duration_ms, " ms")} · Rows: {measured(run.row_count)}
      </Typography>
      {revision !== run.revision && (
        <Alert severity="info">
          This run used a different saved revision. Inspect opens the current
          draft configuration.
        </Alert>
      )}
      {run.error && (
        <Alert severity="error">
          {run.error.code}: {run.error.reason} Inspect the failed block below,
          correct its configuration or resource, then save and rerun.
        </Alert>
      )}
      <Typography component="h3" variant="h2">
        Block evidence
      </Typography>
      {!run.blocks.length && (
        <Typography>No block evidence recorded yet.</Typography>
      )}
      {run.blocks.map((block) => (
        <Paper
          component="section"
          aria-label={`Block ${block.node_id}`}
          variant="outlined"
          sx={{ p: 2 }}
          key={block.node_id}
        >
          <Typography component="h4">
            {block.block_id} · {block.node_id} · {label(block.state)}
          </Typography>
          <Typography>
            Duration: {measured(block.duration_ms, " ms")} · Rows in:{" "}
            {measured(block.rows_in)} · Rows out: {measured(block.rows_out)}
          </Typography>
          {block.error && (
            <Alert severity="error">
              {block.error.code}: {block.error.reason}
            </Alert>
          )}
          <InspectNode id={block.node_id} />
        </Paper>
      ))}
      <Typography component="h3" variant="h2">
        Redacted logs
      </Typography>
      <Typography variant="body2">
        Latest 100 events at most. Credentials and machine paths are redacted by
        the API.
      </Typography>
      {!run.events.length ? (
        <Typography>No log events recorded yet.</Typography>
      ) : (
        <Box
          component="ol"
          aria-label="Run log events"
          tabIndex={0}
          sx={{ maxHeight: 320, overflow: "auto", pl: 4, pr: 1, m: 0 }}
        >
          {run.events.map((event) => (
            <Box component="li" key={event.sequence} sx={{ mb: 1 }}>
              <Typography variant="body2">
                {event.created_at} · {event.level} · {event.code ?? event.kind}:{" "}
                {event.message}
              </Typography>
              {event.node_id && <InspectNode id={event.node_id} />}
            </Box>
          ))}
        </Box>
      )}
    </Stack>
  );
}
function SelectedRun({
  projectId,
  pipelineId,
  runId,
}: {
  projectId: string;
  pipelineId: string;
  runId: string;
}) {
  const detail = useQuery({
    queryKey: ["run", projectId, pipelineId, runId],
    queryFn: ({ signal }) => getRun(projectId, pipelineId, runId, signal),
    gcTime: 0,
    retry: false,
    refetchInterval: (query) =>
      !query.state.data || isActiveRun(query.state.data.state) ? 2000 : false,
  });
  return (
    <Stack spacing={2}>
      <Button
        onClick={() => void detail.refetch()}
        disabled={detail.isFetching}
      >
        Refresh run
      </Button>
      {detail.isPending && (
        <Typography role="status">Loading run evidence…</Typography>
      )}
      {detail.isError && (
        <Alert severity="warning">
          {detail.error.message}{" "}
          {detail.data
            ? "Displayed evidence is stale."
            : "Run evidence is unavailable."}
        </Alert>
      )}
      {detail.data && <Evidence run={detail.data} />}
    </Stack>
  );
}
export function RunMonitor({
  projectId,
  pipelineId,
}: {
  projectId: string;
  pipelineId: string;
}) {
  const online = useSyncExternalStore(
    (notify) => onlineManager.subscribe(notify),
    () => onlineManager.isOnline(),
  );
  const [selected, setSelected] = useState<string | null>(null);
  const runs = useQuery({
    queryKey: ["runs", projectId, pipelineId],
    queryFn: ({ signal }) => listRuns(projectId, pipelineId, signal),
    gcTime: 0,
    retry: false,
    refetchInterval: 2000,
  });
  const runId = selected ?? runs.data?.[0]?.id;
  return (
    <Paper
      component="section"
      aria-label="Run monitoring"
      variant="outlined"
      sx={{ p: 2, minWidth: 0 }}
    >
      <Stack spacing={2}>
        <Typography component="h2" variant="h2">
          Run monitoring
        </Typography>
        <Typography variant="body2">
          Latest 20 runs for this saved pipeline. Runs execute saved revisions;
          unsaved edits are preserved.
        </Typography>
        <Button onClick={() => void runs.refetch()} disabled={runs.isFetching}>
          Refresh runs
        </Button>
        {!online && (
          <Alert severity="warning">
            Offline. Displayed evidence may be stale; monitoring resumes when
            the connection returns.
          </Alert>
        )}
        {runs.isPending && <Typography role="status">Loading runs…</Typography>}
        {runs.isError && (
          <Alert severity="warning">
            {runs.error.message}{" "}
            {runs.data ? "Run list is stale." : "Run list is unavailable."}
          </Alert>
        )}
        {runs.data?.length === 0 && (
          <Typography>
            No runs yet. Execute this saved pipeline through the API or its
            timer to see evidence here.
          </Typography>
        )}
        {runId && (
          <>
            <TextField
              select
              label="Selected run"
              value={runId}
              onChange={(e) => setSelected(e.target.value)}
              slotProps={{ select: { native: true } }}
            >
              {selected && !runs.data?.some((r) => r.id === selected) && (
                <option value={selected}>{selected} (selected history)</option>
              )}
              {runs.data?.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.created_at} · {label(run.state)} · {run.id}
                </option>
              ))}
            </TextField>
            <SelectedRun
              key={runId}
              projectId={projectId}
              pipelineId={pipelineId}
              runId={runId}
            />
          </>
        )}
      </Stack>
    </Paper>
  );
}
