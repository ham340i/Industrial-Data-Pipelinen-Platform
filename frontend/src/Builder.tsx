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
import { useEditorStore } from "./state/editor";

export function Builder({ projectId = null }: { projectId?: string | null }) {
  const draftName = useEditorStore((state) =>
    state.projectId === projectId ? state.draftName : "",
  );
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
        The visual graph editor is planned for a later iteration. This draft
        stays in this tab and is lost when you refresh or switch projects.
      </Alert>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack spacing={3} sx={{ alignItems: "flex-start" }}>
          <TextField
            label="Draft pipeline name"
            value={draftName}
            onChange={(event) => setDraftName(event.target.value)}
            fullWidth
            helperText="Unsaved draft · up to 120 characters"
            slotProps={{ htmlInput: { maxLength: 120 } }}
          />
          <Button
            variant="outlined"
            onClick={() => {
              setDraftName("");
              useEditorStore.getState().selectNode(null);
            }}
            disabled={!draftName}
          >
            Clear draft
          </Button>
        </Stack>
      </Paper>
      <Paper
        variant="outlined"
        sx={{ p: 6, textAlign: "center", borderStyle: "dashed" }}
      >
        <Typography component="h2" variant="h2">
          Your future canvas
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Nodes, connections and validation will appear here when the graph
          editor is available.
        </Typography>
      </Paper>
    </Stack>
  );
}
