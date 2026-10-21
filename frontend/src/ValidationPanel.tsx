import { useState } from "react";
import {
  Alert,
  Button,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { getBlocks } from "./api/blocks";
import type { Diagnostic } from "./api/validation";
import { useEditorStore } from "./state/editor";
import type { ValidationState } from "./state/validation";

function useSubject() {
  const nodes = useEditorStore((state) => state.nodes);
  const edges = useEditorStore((state) => state.edges);
  const catalog = useQuery({
    queryKey: ["blocks"],
    queryFn: ({ signal }) => getBlocks(signal),
    retry: false,
  });
  const name = (id: string | null) => {
    const node = nodes.find((n) => n.id === id);
    if (!node) return null;
    return (
      catalog.data?.find(
        (b) =>
          b.block_id === node.data.block_id &&
          b.version === node.data.block_version,
      )?.name ?? node.data.block_id
    );
  };
  return (d: Diagnostic) => {
    const edge = edges.find((e) => e.id === d.edge_id);
    if (edge)
      return `Connection ${name(edge.source) ?? "?"} → ${name(edge.target) ?? "?"}`;
    return name(d.node_id) ?? (d.edge_id ? "Connection" : "Pipeline");
  };
}

export function ValidationPanel({
  validation,
}: {
  validation: ValidationState;
}) {
  const focusConfiguration = useEditorStore(
    (state) => state.focusConfiguration,
  );
  const nodes = useEditorStore((state) => state.nodes);
  const hasNode = (id: string | null) => nodes.some((n) => n.id === id);
  const subject = useSubject();
  const [ran, setRan] = useState(false);
  const { report, current, error, canRun } = validation;
  const problems = report?.diagnostics ?? [];
  const status = error
    ? null
    : !current
      ? "Checking pipeline…"
      : canRun
        ? "Ready to run. No problems found."
        : `${problems.length} ${problems.length === 1 ? "problem" : "problems"} must be fixed before running.`;
  return (
    <Paper
      component="section"
      aria-label="Pipeline check"
      variant="outlined"
      sx={{ p: 2 }}
    >
      <Stack spacing={2}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={2}
          sx={{ alignItems: { sm: "center" }, justifyContent: "space-between" }}
        >
          <Typography component="h2" variant="h2">
            Pipeline check
          </Typography>
          <Button
            variant="contained"
            disabled={!canRun}
            onClick={() => setRan(true)}
          >
            Run pipeline
          </Button>
        </Stack>
        {status && (
          <Typography role="status" aria-live="polite">
            {status}
          </Typography>
        )}
        {error && (
          <Alert severity="warning">
            {error.message} Running stays disabled until the check succeeds.
          </Alert>
        )}
        {ran && canRun && (
          <Alert severity="info" onClose={() => setRan(false)}>
            The pipeline is valid. Running it becomes available with the local
            executor.
          </Alert>
        )}
        {problems.length > 0 && (
          <List
            dense
            aria-label="Pipeline problems"
            sx={{ opacity: current ? 1 : 0.6 }}
          >
            {problems.map((d, index) => (
              <ListItemButton
                key={`${index}-${d.code}-${d.node_id}-${d.edge_id}-${d.field}`}
                disabled={!hasNode(d.node_id)}
                onClick={() =>
                  d.node_id && focusConfiguration(d.node_id, d.field)
                }
              >
                <ListItemText
                  primary={d.message}
                  secondary={subject(d)}
                  slotProps={{ primary: { color: "error" } }}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Stack>
    </Paper>
  );
}
