import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Stack, Typography } from "@mui/material";
import { listPipelines, openPipeline, savePipeline } from "./api/pipelines";
import { fingerprint, useEditorStore } from "./state/editor";
import { serializeGraph } from "./state/graph";

export function PipelineControls({ projectId }: { projectId: string }) {
  const state = useEditorStore();
  const [offset, setOffset] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ["pipelines", projectId, offset],
    queryFn: ({ signal }) => listPipelines(projectId, offset, signal),
    retry: false,
  });
  const dirty =
    state.savedFingerprint !==
    fingerprint(state.draftName, state.nodes, state.edges);
  const hasEdits =
    dirty &&
    Boolean(
      state.draftName ||
      state.nodes.length ||
      state.edges.length ||
      state.pipelineId,
    );
  async function perform(kind: "save" | "copy" | "open", id?: string) {
    const start = useEditorStore.getState();
    if (start.busy || start.projectId !== projectId) return;
    if (
      kind === "open" &&
      hasEdits &&
      !window.confirm("Discard unsaved changes and open this pipeline?")
    )
      return;
    const generation = start.generation;
    start.setBusy(true);
    setMessage(null);
    const isCurrent = () => {
      const now = useEditorStore.getState();
      return now.projectId === projectId && now.generation === generation;
    };
    try {
      const result =
        kind === "open"
          ? await openPipeline(projectId, id!)
          : await savePipeline(
              projectId,
              start.draftName,
              serializeGraph(start.nodes, start.edges),
              kind === "save" && start.pipelineId && start.revision
                ? { id: start.pipelineId, revision: start.revision }
                : undefined,
            );
      if (isCurrent()) {
        useEditorStore.getState().setBusy(false);
        useEditorStore.getState().loadSaved(result);
        setMessage(kind === "open" ? "Pipeline opened." : "Pipeline saved.");
      }
      await queryClient.invalidateQueries({
        queryKey: ["pipelines", projectId],
      });
    } catch (error) {
      if (isCurrent())
        setMessage(
          error instanceof Error
            ? error.message
            : "Request failed. Your draft is retained.",
        );
    } finally {
      if (isCurrent()) useEditorStore.getState().setBusy(false);
    }
  }
  function exportJSON() {
    const blob = new Blob(
      [JSON.stringify(serializeGraph(state.nodes, state.edges), null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pipeline.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  return (
    <Stack spacing={2}>
      <Typography>
        {state.pipelineId
          ? `Revision ${state.revision} · ${dirty ? "Unsaved changes" : "Saved"}`
          : "New pipeline · Unsaved"}
      </Typography>
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          disabled={state.busy || !state.draftName.trim()}
          onClick={() => void perform("save")}
        >
          Save pipeline
        </Button>
        <Button
          disabled={state.busy || !state.pipelineId || !state.draftName.trim()}
          onClick={() => void perform("copy")}
        >
          Save a copy
        </Button>
        <Button
          disabled={state.busy || dirty || !state.pipelineId}
          onClick={exportJSON}
        >
          Export JSON
        </Button>
      </Stack>
      {state.busy && <Typography role="status">Working…</Typography>}
      {message && (
        <Alert
          severity={
            message === "Pipeline saved." || message === "Pipeline opened."
              ? "success"
              : "warning"
          }
        >
          {message}
        </Alert>
      )}
      <Typography component="h2" variant="h2">
        Saved pipelines
      </Typography>
      {list.isPending && <Typography>Loading pipelines…</Typography>}
      {list.isError && (
        <Alert
          severity="warning"
          action={
            <Button onClick={() => void list.refetch()}>Retry pipelines</Button>
          }
        >
          {list.error.message}
        </Alert>
      )}
      {list.data?.items.length === 0 && (
        <Typography>No saved pipelines yet.</Typography>
      )}
      {list.data?.items.map((p) => (
        <Button
          key={p.id}
          disabled={state.busy}
          onClick={() => void perform("open", p.id)}
        >
          Open {p.name} (revision {p.revision})
        </Button>
      ))}
      {list.data && list.data.total > 20 && (
        <Stack direction="row">
          <Button
            disabled={offset === 0 || state.busy}
            onClick={() => setOffset(offset - 20)}
          >
            Previous pipelines
          </Button>
          <Button
            disabled={offset + 20 >= list.data.total || state.busy}
            onClick={() => setOffset(offset + 20)}
          >
            Next pipelines
          </Button>
        </Stack>
      )}
      <Typography variant="body2">
        Change the pipeline name above and Save pipeline to rename it. Save a
        copy requires a different name.
      </Typography>
    </Stack>
  );
}
