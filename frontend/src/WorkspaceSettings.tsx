// AI contribution: 50% or more AI-generated
import { useEffect, useState } from "react";
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
import { getProject, getProjects } from "./api/projects";
import { listPipelines } from "./api/pipelines";

export function WorkspaceSettings() {
  const client = useQueryClient();
  const projectId = useEditorStore((state) => state.projectId);
  const [draft, setDraft] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState(false);
  const query = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: getWorkspace,
    retry: false,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });
  useEffect(() => {
    if (query.data)
      useEditorStore.getState().switchWorkspace(query.data.root_path);
  }, [query.data]);
  const mutation = useMutation({
    mutationFn: saveWorkspace,
    onSuccess: async (value) => {
      await client.cancelQueries({ queryKey: ["workspace-settings"] });
      const scoped = new Set([
        "projects",
        "project",
        "pipelines",
        "runs",
        "run",
        "artifact",
      ]);
      await client.cancelQueries({
        predicate: (q) => scoped.has(String(q.queryKey[0])),
      });
      client.removeQueries({
        predicate: (q) => scoped.has(String(q.queryKey[0])),
      });
      const previousProject = useEditorStore.getState().projectId;
      let retainDraft = false;
      if (previousProject) {
        try {
          await client.fetchQuery({
            queryKey: ["project", value.root_path, previousProject],
            queryFn: ({ signal }) => getProject(previousProject, signal),
            retry: false,
          });
          retainDraft = true;
        } catch {
          /* The previous draft remains stored with its workspace. */
        }
      }
      useEditorStore.getState().switchWorkspace(value.root_path, retainDraft);
      client.setQueryData(["workspace-settings"], value);
      setDraft(null);
      setRefreshError(false);
      try {
        await client.fetchQuery({
          queryKey: ["projects", value.root_path, 0],
          queryFn: ({ signal }) => getProjects(0, signal),
        });
        const restoredProject = useEditorStore.getState().projectId;
        if (restoredProject)
          await client.fetchQuery({
            queryKey: ["pipelines", value.root_path, restoredProject, 0],
            queryFn: ({ signal }) => listPipelines(restoredProject, 0, signal),
          });
      } catch {
        setRefreshError(true);
      }
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
              helperText="Confirm a folder in File Explorer to save automatically, or enter a path and press Enter."
            />
            <Button
              variant="outlined"
              disabled={
                mutation.isPending || picker.isPending || query.isPending
              }
              onClick={() => picker.mutate(path.trim() || null)}
              sx={{ flexShrink: 0, minHeight: 56 }}
            >
              {picker.isPending
                ? "Choosing folder…"
                : mutation.isPending
                  ? "Saving…"
                  : "Browse…"}
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
            Each pipeline reads from &lt;workspace root&gt;/&lt;project
            name&gt;/&lt;pipeline name&gt;/inputs. Use a Resource Ref such as
            inputs/readings.json in the source block.
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
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
            <Alert
              severity="error"
              action={
                <Button
                  disabled={mutation.isPending || picker.isPending}
                  onClick={() => mutation.mutate(path)}
                >
                  Retry save
                </Button>
              }
            >
              {mutation.error.message} The previous workspace remains active.
              This path has not been saved.
            </Alert>
          )}
          {mutation.isPending && (
            <Typography role="status">Saving workspace…</Typography>
          )}
          {refreshError && (
            <Alert
              severity="warning"
              action={
                <Button component={Link} to="/projects">
                  Open projects
                </Button>
              }
            >
              Workspace saved. Project lists could not be refreshed; open
              Projects to retry.
            </Alert>
          )}
          {mutation.isSuccess && (
            <Alert severity="success">
              {mutation.data.root_path
                ? refreshError
                  ? "Workspace saved."
                  : "Workspace saved. Available projects and pipelines have been reloaded."
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
