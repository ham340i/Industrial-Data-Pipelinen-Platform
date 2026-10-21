import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import { createProject, getProjects } from "./api/projects";
import { selectedProject } from "./state/projectSelection";

export function Projects() {
  const [name, setName] = useState("");
  const [offset, setOffset] = useState(0);
  const [attempted, setAttempted] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useQuery({
    queryKey: ["projects", offset],
    queryFn: ({ signal }) => getProjects(offset, signal),
    retry: false,
    refetchOnWindowFocus: false,
  });
  const creation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}/builder`);
    },
  });
  const normalized = name.trim();
  const valid =
    normalized.length > 0 &&
    [...normalized].length <= 128 &&
    !Array.from(name).some((char) => {
      const code = char.codePointAt(0)!;
      return code < 32 || (code >= 127 && code <= 159);
    });
  const lastProject = selectedProject();
  return (
    <Stack spacing={3}>
      <Typography component="h1" variant="h1">
        Projects
      </Typography>
      <Typography color="text.secondary">
        Create and reopen your local pipeline work.
      </Typography>
      {lastProject && (
        <Button component={Link} to={`/projects/${lastProject}/builder`}>
          Resume last project
        </Button>
      )}
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack
          component="form"
          spacing={2}
          onSubmit={(event) => {
            event.preventDefault();
            setAttempted(true);
            if (valid && !creation.isPending) creation.mutate(normalized);
          }}
        >
          <Typography component="h2" variant="h2">
            Create a project
          </Typography>
          <TextField
            label="Project name"
            value={name}
            disabled={creation.isPending}
            onChange={(event) => {
              setName(event.target.value);
              creation.reset();
            }}
            error={attempted && !valid}
            helperText={
              attempted && !valid
                ? "Enter a name of 1–128 characters without control characters."
                : "Up to 128 characters."
            }
          />
          {creation.isError && (
            <Alert severity="error">{creation.error.message}</Alert>
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={creation.isPending}
          >
            {creation.isPending ? "Creating project…" : "Create project"}
          </Button>
        </Stack>
      </Paper>
      {projects.isPending && (
        <Stack direction="row" spacing={2} role="status">
          <CircularProgress size={20} />
          <Typography>Loading projects…</Typography>
        </Stack>
      )}
      {projects.isError && (
        <Alert
          severity="warning"
          action={
            <Button
              color="inherit"
              disabled={projects.isFetching}
              onClick={() => void projects.refetch()}
            >
              Retry
            </Button>
          }
        >
          {projects.error.message}
        </Alert>
      )}
      {projects.data && (
        <Stack spacing={2}>
          <Typography component="h2" variant="h2">
            Saved projects
          </Typography>
          {projects.data.items.length === 0 && (
            <Typography>
              {offset === 0
                ? "No projects yet. Create your first project above."
                : "No projects on this page."}
            </Typography>
          )}
          <Stack component="ul" spacing={2} sx={{ listStyle: "none", p: 0 }}>
            {projects.data.items.map((project) => (
              <Paper
                component="li"
                key={project.id}
                variant="outlined"
                sx={{ p: 3 }}
              >
                <Stack spacing={1}>
                  <Typography
                    component="h3"
                    variant="h2"
                    sx={{ overflowWrap: "anywhere" }}
                  >
                    {project.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Created {new Date(project.created_at).toLocaleString()}
                  </Typography>
                  <Button
                    component={Link}
                    to={`/projects/${project.id}/builder`}
                    sx={{ overflowWrap: "anywhere", whiteSpace: "normal" }}
                  >
                    Open {project.name}
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </Stack>
      )}
      <Stack direction="row" spacing={2}>
        <Button
          disabled={offset === 0 || projects.isFetching}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Previous page
        </Button>
        <Button
          disabled={
            !projects.data ||
            offset + 20 >= projects.data.total ||
            projects.isFetching
          }
          onClick={() => setOffset(offset + 20)}
        >
          Next page
        </Button>
      </Stack>
    </Stack>
  );
}
