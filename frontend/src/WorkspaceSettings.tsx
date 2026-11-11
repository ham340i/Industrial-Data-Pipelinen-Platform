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
import { getWorkspace, saveWorkspace } from "./api/workspace";
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
  const path = draft ?? query.data?.root_path ?? "";
  const root = query.data?.root_path;
  const source = query.data?.source;
  return (
    <Stack spacing={3}>
      <Typography variant="h1" component="h1">
        Workspace settings
      </Typography>
      <Typography>
        Choose the data folder on the computer running the API. All projects use
        this root, with a separate folder for each project.
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
      {query.data && (
        <Paper variant="outlined" sx={{ p: 3, overflowWrap: "anywhere" }}>
          <Typography component="h2" variant="h2">
            Current configuration
          </Typography>
          <Typography>
            {query.data.ready
              ? "Root folder available"
              : "Workspace needs configuration"}
          </Typography>
          <Typography>{root ?? "No workspace root configured"}</Typography>
          <Typography variant="body2">
            {source === "application"
              ? "Using the saved app setting, overriding LPS_WORKSPACE_ROOT."
              : source === "environment"
                ? "Using LPS_WORKSPACE_ROOT from the API environment."
                : "No app setting or environment root is configured."}
          </Typography>
          {root && projectId && (
            <Typography variant="body2" sx={{ mt: 2 }}>
              Current project inputs: {root.replace(/[\\/]$/, "")}/{projectId}
              /inputs
            </Typography>
          )}
        </Paper>
      )}
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack
          component="form"
          spacing={2}
          onSubmit={(event) => {
            event.preventDefault();
            if (path.trim() && !mutation.isPending) mutation.mutate(path);
          }}
        >
          <TextField
            label="Workspace root folder"
            fullWidth
            value={path}
            disabled={mutation.isPending || query.isPending}
            onChange={(event) => {
              setDraft(event.target.value);
              mutation.reset();
            }}
            slotProps={{ htmlInput: { maxLength: 4096 } }}
            helperText="Enter one of the permitted folder paths below exactly as shown. Save validates access and creates project inputs folders."
          />
          {query.data?.allowed_roots.map((permittedRoot) => (
            <Typography
              key={permittedRoot}
              variant="body2"
              sx={{ overflowWrap: "anywhere" }}
            >
              Permitted folder: {permittedRoot}
            </Typography>
          ))}
          <Typography variant="body2">
            To permit another folder, set LPS_ALLOWED_WORKSPACE_ROOTS to a JSON
            list of absolute paths on the API computer and restart the API.
          </Typography>
          <Typography variant="body2">
            Changing the root applies to subsequent previews without restarting
            the API. Existing files stay in their current folders; move or copy
            your data separately if needed.
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
                disabled={mutation.isPending}
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
