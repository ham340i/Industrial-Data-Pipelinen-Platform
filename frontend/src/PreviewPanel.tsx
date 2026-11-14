import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { getBlocks, type BlockMetadata } from "./api/blocks";
import {
  PreviewError,
  type PreviewRequest,
  type PreviewResult,
} from "./api/preview";
import { useEditorStore } from "./state/editor";
import { semanticDefinition } from "./state/validation";
import { previewIdentity, usePreview } from "./state/preview";

function Results({ result }: { result: PreviewResult }) {
  const [tab, setTab] = useState("sample");
  return (
    <Stack spacing={1}>
      <Typography role="status">
        {result.sample_row_count} sampled rows ·{" "}
        {result.full_row_count === null
          ? "Full row count unknown"
          : result.full_count_scope === "file_metadata"
            ? `${result.full_row_count} total rows reported by file metadata`
            : `${result.full_row_count} rows in complete input`}
      </Typography>
      <Typography variant="body2">
        Leading rows in source order. Inspected {result.inspected_row_count}{" "}
        rows
        {result.truncated
          ? "; sample is truncated."
          : result.full_count_scope === "file_metadata"
            ? "; sampled all rows reported by file metadata."
            : "; reached the end of the input."}{" "}
        Null counts describe only the returned sample and do not establish
        whole-input quality.
      </Typography>
      <Typography variant="body2">
        {
          {
            declared: "Configured schema, checked against sampled rows.",
            header:
              "Header-based string schema. Columns may contain nulls; unsampled rows have not been validated.",
            sample:
              "Schema inferred from sampled rows. Columns may contain nulls; unsampled rows may have different types or keys.",
            file_metadata:
              "Schema reported by file metadata, checked against sampled rows. Unsampled data has not been validated.",
          }[result.schema_scope]
        }
      </Typography>
      <Typography variant="caption">
        Limits: {result.effective_limits.max_rows} rows /{" "}
        {result.effective_limits.max_cells} cells per step. Read{" "}
        {result.source_read_bytes} bytes in {result.elapsed_ms} ms across{" "}
        {result.evaluated_node_ids.length} nodes.
      </Typography>
      <Tabs
        value={tab}
        onChange={(_, value: string) => setTab(value)}
        aria-label="Preview views"
        variant="scrollable"
        allowScrollButtonsMobile
      >
        <Tab
          value="sample"
          label="Sample"
          id="preview-sample-tab"
          aria-controls="preview-sample-panel"
        />
        <Tab
          value="schema"
          label="Schema"
          id="preview-schema-tab"
          aria-controls="preview-schema-panel"
        />
        <Tab
          value="nulls"
          label="Null summary"
          id="preview-nulls-tab"
          aria-controls="preview-nulls-panel"
        />
      </Tabs>
      <Box
        role="tabpanel"
        id={`preview-${tab}-panel`}
        aria-labelledby={`preview-${tab}-tab`}
        sx={{ minWidth: 0 }}
      >
        {tab === "sample" && result.rows.length === 0 && (
          <Alert severity="info">
            No rows in this input. Open the Schema tab to inspect its columns.
          </Alert>
        )}
        <TableContainer tabIndex={0} sx={{ maxHeight: 360, maxWidth: "100%" }}>
          <Table size="small" stickyHeader aria-label={`Preview ${tab}`}>
            <TableHead>
              <TableRow>
                {(tab === "sample"
                  ? result.data_schema.columns.map((c) => c.name)
                  : tab === "schema"
                    ? ["Column", "Type", "Nullable"]
                    : ["Column", "Nulls in sample", "Sample rows"]
                ).map((name) => (
                  <TableCell key={name}>{name}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {tab === "sample"
                ? result.rows.map((row, index) => (
                    <TableRow key={index}>
                      {result.data_schema.columns.map((c) => (
                        <TableCell
                          key={c.name}
                          sx={{ maxWidth: 280, overflowWrap: "anywhere" }}
                        >
                          {row[c.name] === null ? (
                            <Box
                              component="span"
                              sx={{
                                fontStyle: "italic",
                                color: "text.secondary",
                              }}
                            >
                              null
                            </Box>
                          ) : (
                            String(row[c.name])
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                : tab === "schema"
                  ? result.data_schema.columns.map((c) => (
                      <TableRow key={c.name}>
                        <TableCell>{c.name}</TableCell>
                        <TableCell>{c.dtype}</TableCell>
                        <TableCell>{c.nullable ? "Yes" : "No"}</TableCell>
                      </TableRow>
                    ))
                  : result.nulls.map((n) => (
                      <TableRow key={n.column}>
                        <TableCell>{n.column}</TableCell>
                        <TableCell>{n.null_count}</TableCell>
                        <TableCell>{result.sample_row_count}</TableCell>
                      </TableRow>
                    ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Stack>
  );
}

function Session({
  projectId,
  request,
  disabled,
}: {
  projectId: string;
  request: PreviewRequest;
  disabled: boolean;
}) {
  const { state, refresh, cancel } = usePreview(projectId, request);
  const error = state.status === "error" ? state.error : null;
  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          disabled={disabled || state.status === "loading"}
          onClick={() => void refresh()}
        >
          {state.status === "success"
            ? "Refresh preview"
            : state.status === "error"
              ? "Retry preview"
              : "Preview selected node"}
        </Button>
        {state.status === "loading" && (
          <Button onClick={cancel}>Cancel preview</Button>
        )}
      </Stack>
      {state.status === "idle" && (
        <Typography>
          Preview the current selection to see its schema and a bounded sample.
        </Typography>
      )}
      {state.status === "loading" && (
        <Typography role="status">Reading bounded preview…</Typography>
      )}
      {error && (
        <Alert
          severity="error"
          action={
            error instanceof PreviewError &&
            [
              "workspace_required",
              "workspace_settings_unavailable",
              "workspace_project_folder",
            ].includes(error.code) ? (
              <Button href="#/settings/workspace">Configure workspace</Button>
            ) : error instanceof PreviewError && error.nodeId ? (
              <Button
                onClick={() =>
                  useEditorStore
                    .getState()
                    .focusConfiguration(error.nodeId!, error.field)
                }
              >
                Configure node
              </Button>
            ) : undefined
          }
        >
          {error.message}
          {error instanceof PreviewError && (
            <Typography variant="caption" component="div">
              {error.field ? `Field: ${error.field}. ` : ""}
              {error.port ? `Output: ${error.port}. ` : ""}Reference:{" "}
              {error.correlationId}
            </Typography>
          )}
        </Alert>
      )}
      {state.status === "success" && <Results result={state.result} />}
    </Stack>
  );
}

function Controls({
  projectId,
  block,
}: {
  projectId: string;
  block: BlockMetadata;
}) {
  const state = useEditorStore();
  const [rows, setRows] = useState("20");
  const [cells, setCells] = useState("2000");
  const outputs = block.outputs.filter((p) => p.kind === "data");
  const [output, setOutput] = useState(outputs[0]?.name ?? "");
  const port = outputs.some((p) => p.name === output)
    ? output
    : (outputs[0]?.name ?? "");
  const valid =
    Number.isInteger(Number(rows)) &&
    Number(rows) >= 1 &&
    Number(rows) <= 1000 &&
    Number.isInteger(Number(cells)) &&
    Number(cells) >= 1 &&
    Number(cells) <= 10000 &&
    !!port;
  const request: PreviewRequest = {
    definition: semanticDefinition(state.nodes, state.edges),
    node_id: state.selectedNodeId!,
    output_port: port,
    limits: { max_rows: Number(rows), max_cells: Number(cells) },
  };
  return (
    <Stack spacing={2}>
      <Typography>
        {block.name} · CSV, JSON and Parquet paths through Select Columns
        support bounded preview. Other upstream blocks report their limitations.
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <TextField
          select
          label="Preview output"
          sx={{ minWidth: 160 }}
          value={port}
          onChange={(e) => setOutput(e.target.value)}
          slotProps={{ select: { native: true } }}
        >
          {outputs.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </TextField>
        <TextField
          type="number"
          label="Preview rows"
          value={rows}
          onChange={(e) => setRows(e.target.value)}
          slotProps={{ htmlInput: { min: 1, max: 1000 } }}
          helperText="1–1,000"
        />
        <TextField
          type="number"
          label="Preview cells"
          value={cells}
          onChange={(e) => setCells(e.target.value)}
          slotProps={{ htmlInput: { min: 1, max: 10000 } }}
          helperText="1–10,000"
        />
      </Stack>
      <Session
        key={previewIdentity(projectId, state.generation, request, state.busy)}
        projectId={projectId}
        request={request}
        disabled={!valid || state.busy}
      />
    </Stack>
  );
}

export function PreviewPanel({ projectId }: { projectId: string | null }) {
  const node = useEditorStore((s) =>
    s.nodes.find((n) => n.id === s.selectedNodeId),
  );
  const generation = useEditorStore((s) => s.generation);
  const catalog = useQuery({
    queryKey: ["blocks"],
    queryFn: ({ signal }) => getBlocks(signal),
    retry: false,
  });
  const block = catalog.data?.find(
    (b) =>
      b.block_id === node?.data.block_id &&
      b.version === node?.data.block_version,
  );
  let content;
  if (!node)
    content = <Typography>Select a node to preview its output.</Typography>;
  else if (!projectId)
    content = (
      <Typography>Open a project to preview its local data.</Typography>
    );
  else if (catalog.isPending)
    content = (
      <Typography role="status">Loading preview capabilities…</Typography>
    );
  else if (catalog.isError)
    content = (
      <Alert
        severity="error"
        action={
          <Button onClick={() => void catalog.refetch()}>
            Retry preview capabilities
          </Button>
        }
      >
        Cannot load preview capabilities.
      </Alert>
    );
  else if (!block)
    content = (
      <Alert severity="warning">This block version is unavailable.</Alert>
    );
  else if (!block.supports_preview)
    content = (
      <Alert severity="info">
        {block.preview_reason ?? "Preview is not supported by this block."}
      </Alert>
    );
  else
    content = (
      <Controls
        key={`${projectId}:${generation}:${node.id}`}
        projectId={projectId}
        block={block}
      />
    );
  return (
    <Paper
      component="section"
      aria-label="Selected-node preview"
      variant="outlined"
      sx={{ p: 2, minWidth: 0, overflow: "hidden" }}
    >
      <Typography component="h2" variant="h2" sx={{ mb: 2 }}>
        Selected-node preview
      </Typography>
      {content}
    </Paper>
  );
}
