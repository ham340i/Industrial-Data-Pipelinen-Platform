// AI contribution: 50% or more AI-generated
import { RunResult } from "./RunResult";
import { useState, useSyncExternalStore } from "react";
import {
  onlineManager,
  useIsFetching,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Alert,
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
function Evidence({ run }: { run: RunDetail }) {
  const state = useEditorStore();
  const sameRevision = state.revision === run.revision;
  return (
    <Stack spacing={2}>
      {!sameRevision && (
        <Alert severity="info">
          This run used a different saved revision. Configuration links are
          disabled.
        </Alert>
      )}
      <RunResult
        run={run}
        onInspect={
          sameRevision && !state.busy
            ? (id) => {
                if (state.nodes.some((node) => node.id === id))
                  state.focusConfiguration(id, null);
              }
            : undefined
        }
      />
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
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["runs", projectId, pipelineId, offset],
    queryFn: ({ signal }) => listRuns(projectId, pipelineId, signal, offset),
    gcTime: 0,
    retry: false,
    refetchInterval: 2000,
  });
  const runId = selected ?? runs.data?.[0]?.id;
  const detailFetching = useIsFetching({
    queryKey: ["run", projectId, pipelineId, runId],
    exact: true,
  });
  async function refresh() {
    await Promise.all([
      runs.refetch(),
      ...(runId
        ? [
            queryClient.refetchQueries({
              queryKey: ["run", projectId, pipelineId, runId],
              exact: true,
              type: "active",
            }),
          ]
        : []),
    ]);
  }
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
          Runs for this saved pipeline, 20 per page. Runs execute saved
          revisions; unsaved edits are preserved.
        </Typography>
        <Button
          onClick={() => void refresh()}
          disabled={runs.isFetching || detailFetching > 0}
        >
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
            No runs yet. Use Run saved pipeline to execute this graph and see
            evidence here.
          </Typography>
        )}
        <Stack direction="row" spacing={1}>
          <Button
            disabled={(runs.data?.length ?? 0) < 20 || runs.isFetching}
            onClick={() => {
              setSelected(null);
              setOffset(offset + 20);
            }}
          >
            Previous 20 runs
          </Button>
          <Button
            disabled={offset === 0 || runs.isFetching}
            onClick={() => {
              setSelected(null);
              setOffset(Math.max(0, offset - 20));
            }}
          >
            Next 20 runs
          </Button>
        </Stack>
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
