import { useEffect } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { PipelineControls } from "./PipelineControls";
import { Canvas } from "./Canvas";
import { useEditorStore } from "./state/editor";

export function Builder({ projectId = null }: { projectId?: string | null }) {
  const draftName = useEditorStore((state) =>
    state.projectId === projectId ? state.draftName : "",
  );
  const busy = useEditorStore((state) => state.busy);
  const nodeCount = useEditorStore((state) => state.nodes.length);
  const setDraftName = useEditorStore((state) => state.setDraftName);
  const setProject = useEditorStore((state) => state.setProject);
  useEffect(() => setProject(projectId), [projectId, setProject]);
  return (
    <Stack spacing={3}>
      <Box>
        <Typography component="h1" variant="h1">
          Pipeline builder
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Prepare your workspace.
        </Typography>
      </Box>
      <Alert severity="info">
        {projectId
          ? "Save your pipeline to keep its graph and configuration. Unsaved changes are lost on refresh or project switch."
          : "Choose a project to save pipelines. This draft stays in this tab and is lost on refresh."}
      </Alert>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack spacing={3} sx={{ alignItems: "flex-start" }}>
          <TextField
            label="Draft pipeline name"
            disabled={busy}
            value={draftName}
            onChange={(event) => setDraftName(event.target.value)}
            fullWidth
            helperText="Unsaved draft · up to 128 characters"
            slotProps={{ htmlInput: { maxLength: 128 } }}
          />
          <Button
            variant="outlined"
            onClick={() => {
              useEditorStore.getState().clearDraft();
            }}
            disabled={busy || (!draftName && !nodeCount)}
          >
            Clear draft
          </Button>
        </Stack>
      </Paper>
      {projectId && <PipelineControls key={projectId} projectId={projectId} />}
      <Box inert={busy}>
        <Canvas />
      </Box>
    </Stack>
  );
}
