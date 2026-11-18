// AI contribution: 50% or more AI-generated
import { useState } from "react";
import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import { downloadRunLog, type RunDetail } from "./api/runs";
import { normalizeApiError } from "./api/client";
import { OutputInspection } from "./OutputInspection";
import { useEditorStore } from "./state/editor";

export function RunResult({
  run,
  onInspect,
  showStatus = true,
  showDownload = true,
}: {
  run: RunDetail;
  onInspect?: (nodeId: string) => void;
  showStatus?: boolean;
  showDownload?: boolean;
}) {
  const nodes = useEditorStore((s) => s.nodes);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const failed = run.blocks.filter((block) => block.state === "failed");
  async function download() {
    setDownloading(true);
    setError(null);
    try {
      await downloadRunLog(run.id);
    } catch (problem) {
      setError(normalizeApiError(problem).message);
    } finally {
      setDownloading(false);
    }
  }
  return (
    <Stack spacing={2} sx={{ overflowWrap: "anywhere", minWidth: 0 }}>
      {showStatus && (
        <Typography role="status">
          {run.state === "succeeded"
            ? "Completed"
            : run.state[0].toUpperCase() + run.state.slice(1)}{" "}
          · Run {run.id}
        </Typography>
      )}
      <Typography>
        Saved revision {run.revision} · Duration:{" "}
        {run.duration_ms === null ? "Unknown" : `${run.duration_ms} ms`} · Rows:{" "}
        {run.row_count ?? "Unknown"}
      </Typography>
      {run.error && (
        <Alert severity="error">
          {run.error.code}: {run.error.reason}
        </Alert>
      )}
      {failed.length > 0 && (
        <Typography component="h3" variant="h2">
          Failed blocks
        </Typography>
      )}
      {failed.map((block) => (
        <Paper
          component="section"
          aria-label={`Block ${block.node_id}`}
          variant="outlined"
          sx={{ p: 2 }}
          key={block.node_id}
        >
          <Typography>
            {block.block_id} · {block.node_id} · Failed
          </Typography>
          {block.error && (
            <Typography>
              {block.error.code}: {block.error.reason}
            </Typography>
          )}
          {onInspect && nodes.some((node) => node.id === block.node_id) && (
            <Button onClick={() => onInspect(block.node_id)}>
              Configure failed block {block.node_id}
            </Button>
          )}
        </Paper>
      ))}
      <OutputInspection run={run} />
      {showDownload && (
        <>
          <Button
            disabled={downloading}
            onClick={() => void download()}
            sx={{ alignSelf: "flex-start" }}
          >
            {downloading ? "Downloading log…" : "Download log"}
          </Button>
          {error && <Alert severity="error">{error}</Alert>}
        </>
      )}
    </Stack>
  );
}
