import { createContext, useContext, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { getBlocks, type BlockMetadata } from "./api/blocks";
import type { Diagnostic } from "./api/validation";
import { useEditorStore } from "./state/editor";
import type { BlockNode } from "./state/graph";
import { markEdges, placeDiagnostics } from "./state/validation";

const Catalog = createContext<BlockMetadata[]>([]);
const NodeProblems = createContext<Map<string, Diagnostic[]>>(new Map());
function BlockCard({ id, data, selected }: NodeProps<BlockNode>) {
  const block = useContext(Catalog).find(
    (b) => b.block_id === data.block_id && b.version === data.block_version,
  );
  const problems = useContext(NodeProblems).get(id) ?? [];
  return (
    <Paper
      variant="outlined"
      aria-invalid={problems.length > 0}
      sx={{
        p: 2,
        minWidth: 210,
        maxWidth: 280,
        borderColor: problems.length
          ? "error.main"
          : selected
            ? "primary.main"
            : "divider",
        borderWidth: selected || problems.length ? 2 : 1,
      }}
    >
      <Typography sx={{ fontWeight: "bold" }}>
        {block?.name ?? data.block_id}
      </Typography>
      <Typography variant="caption">
        {block?.category ?? "Unavailable block"} · v{data.block_version}
      </Typography>
      {(["inputs", "outputs"] as const).map((direction) => (
        <Box key={direction}>
          {block?.[direction].map((port) => (
            <Box
              key={port.name}
              sx={{
                position: "relative",
                py: 0.5,
                textAlign: direction === "inputs" ? "left" : "right",
              }}
            >
              <Handle
                id={port.name}
                type={direction === "inputs" ? "target" : "source"}
                position={
                  direction === "inputs" ? Position.Left : Position.Right
                }
                aria-label={`${direction} ${port.name}`}
              />
              <Typography
                variant="caption"
                color={
                  direction === "inputs" &&
                  problems.some((p) => p.port === port.name)
                    ? "error"
                    : undefined
                }
              >
                {port.name} ({port.kind})
              </Typography>
            </Box>
          ))}
        </Box>
      ))}
      {problems.length > 0 && (
        <Box
          component="ul"
          aria-label={`Problems in ${block?.name ?? data.block_id}`}
          sx={{ m: 0, mt: 1, pl: 2 }}
        >
          {problems.map((p, index) => (
            <Typography
              key={index}
              component="li"
              variant="caption"
              color="error"
              sx={{ display: "list-item" }}
            >
              {p.message}
            </Typography>
          ))}
        </Box>
      )}
    </Paper>
  );
}
const nodeTypes = { block: BlockCard };
function GraphCanvas({ diagnostics }: { diagnostics: Diagnostic[] }) {
  const state = useEditorStore();
  const theme = useTheme();
  const placed = useMemo(
    () => placeDiagnostics(diagnostics, state.nodes, state.edges),
    [diagnostics, state.nodes, state.edges],
  );
  // Highlighting is derived for display only; the stored draft is untouched.
  const edges = useMemo(
    () => markEdges(state.edges, placed.byEdge, theme.palette.error.main),
    [state.edges, placed, theme],
  );
  const [search, setSearch] = useState("");
  const { screenToFlowPosition } = useReactFlow();
  const catalog = useQuery({
    queryKey: ["blocks"],
    queryFn: ({ signal }) => getBlocks(signal),
    retry: false,
  });
  const blocks = catalog.data ?? [];
  return (
    <Stack spacing={2}>
      {catalog.isPending && (
        <Typography role="status">Loading block library…</Typography>
      )}
      {catalog.isError && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => void catalog.refetch()}>
              Retry library
            </Button>
          }
        >
          {catalog.error.message}
        </Alert>
      )}
      {state.error && <Alert severity="warning">{state.error}</Alert>}
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <Paper
          component="aside"
          variant="outlined"
          sx={{ p: 2, width: { md: 280 }, flexShrink: 0 }}
        >
          <Typography component="h2" variant="h2">
            Block library
          </Typography>
          <TextField
            label="Search blocks"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            fullWidth
            sx={{ my: 2 }}
          />
          {catalog.isSuccess && !blocks.length && (
            <Typography>No blocks are registered.</Typography>
          )}
          {blocks
            .filter((b) =>
              `${b.name} ${b.category} ${b.block_id}`
                .toLowerCase()
                .includes(search.toLowerCase()),
            )
            .map((b) => (
              <Box
                key={`${b.block_id}@${b.version}`}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData(
                    "application/x-pipeline-block",
                    JSON.stringify([b.block_id, b.version]),
                  );
                  e.dataTransfer.effectAllowed = "copy";
                }}
                sx={{ mb: 2 }}
              >
                <Typography sx={{ fontWeight: "bold" }}>{b.name}</Typography>
                <Typography variant="body2">
                  {b.category} · v{b.version}
                </Typography>
                <Typography variant="caption" component="p">
                  Inputs:{" "}
                  {b.inputs.map((p) => `${p.name} (${p.kind})`).join(", ") ||
                    "none"}
                </Typography>
                <Typography variant="caption" component="p">
                  Outputs:{" "}
                  {b.outputs.map((p) => `${p.name} (${p.kind})`).join(", ") ||
                    "none"}
                </Typography>
                <Button onClick={() => state.addBlock(b)}>Add {b.name}</Button>
              </Box>
            ))}
        </Paper>
        <Catalog value={blocks}>
          <NodeProblems value={placed.byNode}>
            <Box
              aria-label="Pipeline canvas"
              sx={{
                height: 560,
                flex: 1,
                minWidth: 0,
                border: "1px solid",
                borderColor: "divider",
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "copy";
              }}
              onDrop={(e) => {
                e.preventDefault();
                try {
                  const key: unknown = JSON.parse(
                    e.dataTransfer.getData("application/x-pipeline-block"),
                  );
                  const block =
                    Array.isArray(key) &&
                    blocks.find(
                      (b) => b.block_id === key[0] && b.version === key[1],
                    );
                  if (block)
                    state.addBlock(
                      block,
                      screenToFlowPosition({ x: e.clientX, y: e.clientY }),
                    );
                } catch {
                  /* Foreign drag data does not alter the draft. */
                }
              }}
            >
              <ReactFlow<BlockNode>
                nodes={state.nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodesChange={state.changeNodes}
                onEdgesChange={state.changeEdges}
                onConnect={(c) => state.connect(c, blocks)}
                onNodeClick={(_, n) => state.selectNode(n.id)}
                onPaneClick={() => state.selectNode(null)}
                deleteKeyCode={["Backspace", "Delete"]}
                fitView
                fitViewOptions={{ maxZoom: 1 }}
              >
                <Background />
                <Controls />
              </ReactFlow>
            </Box>
          </NodeProblems>
        </Catalog>
      </Stack>
      <Button
        onClick={state.deleteSelected}
        disabled={!state.selectedNodeId && !state.edges.some((e) => e.selected)}
      >
        Delete selected
      </Button>
      <Typography variant="body2">
        Drag a block or use Add. Select nodes to move them with arrow keys;
        press Delete to remove nodes or connections. Connect an output handle to
        a compatible input.
      </Typography>
    </Stack>
  );
}
export function Canvas({ diagnostics = [] }: { diagnostics?: Diagnostic[] }) {
  return (
    <ReactFlowProvider>
      <GraphCanvas diagnostics={diagnostics} />
    </ReactFlowProvider>
  );
}
