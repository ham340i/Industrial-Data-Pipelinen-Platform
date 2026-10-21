import { useEffect } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import { Link, Navigate, useParams } from "react-router-dom";
import { Builder } from "./Builder";
import { ApiError } from "./api/client";
import { isProjectId, useProject } from "./api/projects";
import {
  forgetProject,
  rememberProject,
  selectedProject,
} from "./state/projectSelection";

export function BuilderEntry() {
  const projectId = selectedProject();
  return projectId ? (
    <Navigate to={`/projects/${projectId}/builder`} replace />
  ) : (
    <Builder />
  );
}
export function ProjectWorkspace() {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const missing =
    project.error instanceof ApiError && project.error.status === 404;
  useEffect(() => {
    if (missing) forgetProject(projectId);
    else if (project.isSuccess && !project.isFetching && project.data)
      rememberProject(project.data.id);
  }, [project.data, project.isSuccess, project.isFetching, projectId, missing]);
  if (!isProjectId(projectId) || missing)
    return (
      <Stack spacing={2}>
        <Typography component="h1" variant="h1">
          Project unavailable
        </Typography>
        <Typography>
          This project link is invalid or the project no longer exists.
        </Typography>
        <Button component={Link} to="/projects">
          Choose a project
        </Button>
      </Stack>
    );
  if (project.isPending || project.isFetching)
    return (
      <Stack role="status" direction="row" spacing={2}>
        <CircularProgress size={20} />
        <Typography>Opening project…</Typography>
      </Stack>
    );
  if (project.isError)
    return (
      <Alert
        severity="warning"
        action={
          <Button
            color="inherit"
            disabled={project.isFetching}
            onClick={() => void project.refetch()}
          >
            Retry
          </Button>
        }
      >
        {project.error.message}
      </Alert>
    );
  return (
    <Stack spacing={3}>
      <Typography component="h2" variant="h2" sx={{ overflowWrap: "anywhere" }}>
        Project: {project.data.name}
      </Typography>
      <Button component={Link} to="/projects">
        Choose another project
      </Button>
      <Builder projectId={project.data.id} />
    </Stack>
  );
}
