// AI contribution: 50% or more AI-generated
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import {
  ARTIFACT_PAGE_SIZE,
  queryArtifact,
  type ArtifactIdentity,
} from "./api/artifacts";
import type { RunDetail } from "./api/runs";
import { ApiError } from "./api/client";

function inspectionError(error: Error): string {
  if (error instanceof ApiError) {
    if (error.status === 409)
      return "The output file is unavailable or could not be read. It may have been replaced by a later run. Inspect that run's output or rerun this revision.";
    if (error.status === 422)
      return "This output cannot be inspected with the current query. Inspection requires a Parquet file with a registered schema and up to 100 selected columns.";
    if (error.status === 404)
      return "This output is no longer available in the selected workspace.";
  }
  return error.message;
}

function ArtifactRows({ identity }: { identity: ArtifactIdentity }) {
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: [
      "artifact-rows",
      identity.artifactId,
      identity.runId,
      identity.revisionId,
      offset,
    ],
    queryFn: ({ signal }) => queryArtifact(identity, offset, signal),
    retry: false,
    gcTime: 0,
    staleTime: 0,
  });
  return (
    <Stack spacing={1}>
      {query.isPending && (
        <Typography role="status">Loading output rows…</Typography>
      )}
      {query.isError && (
        <Alert
          severity="warning"
          action={
            !(
              query.error instanceof ApiError && query.error.status === 422
            ) && (
              <Button onClick={() => void query.refetch()}>
                Retry output rows
              </Button>
            )
          }
        >
          {inspectionError(query.error)}
        </Alert>
      )}
      {query.data && !query.isError && (
        <>
          <Typography role="status">
            {query.data.rows.length} rows shown · offset {offset} · up to{" "}
            {ARTIFACT_PAGE_SIZE} rows per page
          </Typography>
          <TableContainer tabIndex={0} sx={{ maxHeight: 360 }}>
            <Table size="small" aria-label="Parquet output rows">
              <TableHead>
                <TableRow>
                  {query.data.columns.map((column) => (
                    <TableCell key={column}>{column}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {query.data.rows.map((row, index) => (
                  <TableRow key={index}>
                    {row.map((value, cell) => (
                      <TableCell key={cell}>
                        {value === null ? "null" : String(value)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          {query.data.rows.length === 0 && (
            <Typography>No rows in this output page.</Typography>
          )}
        </>
      )}
      <Stack direction="row" spacing={1}>
        <Button
          disabled={offset === 0 || query.isFetching}
          onClick={() => setOffset(Math.max(0, offset - ARTIFACT_PAGE_SIZE))}
        >
          Previous output rows
        </Button>
        <Button
          disabled={!query.data?.has_more || query.isFetching || query.isError}
          onClick={() => setOffset(offset + ARTIFACT_PAGE_SIZE)}
        >
          Next output rows
        </Button>
      </Stack>
    </Stack>
  );
}

function Output({
  output,
  run,
}: {
  output: RunDetail["outputs"][number];
  run: RunDetail;
}) {
  const [open, setOpen] = useState(false);
  const inspectable = output.artifact_ref.toLowerCase().endsWith(".parquet");
  return (
    <Stack spacing={1}>
      <Typography>
        {output.name} · {output.row_count ?? "unknown"} rows ·{" "}
        {output.artifact_ref}
      </Typography>
      {inspectable ? (
        <Button aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Inspect"} output {output.name}
        </Button>
      ) : (
        <Typography>
          In-app row inspection supports Parquet outputs. Open this file in your
          workspace to view its contents, or use a Parquet Sink to inspect rows
          here.
        </Typography>
      )}
      {inspectable && open && (
        <ArtifactRows
          identity={{
            artifactId: output.id,
            runId: run.id,
            revisionId: run.pipeline_revision_id,
          }}
        />
      )}
    </Stack>
  );
}

export function OutputInspection({ run }: { run: RunDetail }) {
  return (
    <Stack component="section" aria-label="Output inspection" spacing={2}>
      <Typography component="h3" variant="h2">
        Output artifacts
      </Typography>
      {!run.outputs.length && (
        <Typography>
          No indexed artifacts are available for this run.
        </Typography>
      )}
      {run.outputs.map((output) => (
        <Output
          key={`${run.id}:${output.id}:${run.pipeline_revision_id}`}
          output={output}
          run={run}
        />
      ))}
    </Stack>
  );
}
