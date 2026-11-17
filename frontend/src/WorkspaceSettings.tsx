// AI contribution: 50% or more AI-generated
import { useState } from "react";
import {
  Alert,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getWorkspace,
  pickWorkspaceFolder,
  saveWorkspace,
} from "./api/workspace";
import { useEditorStore } from "./state/editor";

export function WorkspaceSettings() {
  const client = useQueryClient();
  const projectId = useEditorStore((state) => state.projectId);
  const [draft, setDraft] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: getWorkspace,
    retry: false,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });
  const mutation = useMutation({
    mutationFn: saveWorkspace,
    onSuccess: (value) => {
      client.setQueryData(["workspace-settings"], value);
      setDraft(null);
    },
  });
  const picker = useMutation({
    mutationFn: pickWorkspaceFolder,
    retry: false,
    onSuccess: (selectedPath) => {
      if (selectedPath !== null) {
        setDraft(selectedPath);
        mutation.mutate(selectedPath);
      }
    },
  });
  const path = draft ?? query.data?.root_path ?? "";
  const source = query.data?.source;
  return (
    <Stack spacing={3}>
      <Typography variant="h1" component="h1">
        Settings
      </Typography>
      {query.isPending && (
        <Typography role="status">Loading workspace settings…</Typography>
      )}
      {query.isError && (
        <Alert
          severity="error"
          action={<Button onClick={() => void query.refetch()}>Retry</Button>}
        >
          {query.error.message}
        </Alert>
      )}
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack
          component="form"
          spacing={2}
          onSubmit={(event) => {
            event.preventDefault();
            if (path.trim() && !mutation.isPending && !picker.isPending)
              mutation.mutate(path);
          }}
        >
          <Typography component="h2" variant="h2">
            Current workspace configuration
          </Typography>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            sx={{ alignItems: { sm: "flex-start" } }}
          >
            <TextField
              label="Workspace root folder"
              fullWidth
              value={path}
              disabled={
                mutation.isPending || picker.isPending || query.isPending
              }
              onChange={(event) => {
                setDraft(event.target.value);
                mutation.reset();
                picker.reset();
              }}
              slotProps={{ htmlInput: { maxLength: 4096 } }}
              helperText="Browse or enter a folder path. Save validates access and prepares project inputs folders."
            />
            <Button
              variant="outlined"
              disabled={
                mutation.isPending || picker.isPending || query.isPending
              }
              onClick={() => picker.mutate(path.trim() || null)}
              sx={{ flexShrink: 0, minHeight: 56 }}
            >
              {picker.isPending ? "Choosing folder…" : (mutation.isPending ? "Saving…" : "Browse…")}             
            </Button>
          </Stack>
          {picker.isError && (
            <Alert severity="error">{picker.error.message}</Alert>
          )}
          <Typography variant="body2">
            Browse opens File Explorer on this Windows computer. For a remote
            API, enter a permitted folder path available on that computer.
          </Typography>
          <Typography variant="body2">
            Each project reads from &lt;workspace root&gt;/&lt;project
            ID&gt;/inputs. Use a Resource Ref such as inputs/readings.json in
            the source block.
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
            <Button
              type="submit"
              variant="contained"
              disabled={!path.trim() || mutation.isPending || query.isPending}
            >
              {mutation.isPending ? "Saving…" : "Save workspace"}
            </Button>
            {source === "application" && (
              <Button
                disabled={mutation.isPending || picker.isPending}
                onClick={() => mutation.mutate(null)}
              >
                Use environment setting
              </Button>
            )}
          </Stack>
          {mutation.isError && (
            <Alert severity="error">{mutation.error.message}</Alert>
          )}
          {mutation.isSuccess && (
            <Alert severity="success">
              {mutation.data.root_path
                ? "Workspace saved. Project data folders are ready; previews can use the new setting now."
                : "App setting removed. No environment root is configured."}
            </Alert>
          )}
        </Stack>
      </Paper>
      {projectId && (
        <Button component={Link} to={`/projects/${projectId}/builder`}>
          Return to project builder
        </Button>
      )}
    </Stack>
  );
}
