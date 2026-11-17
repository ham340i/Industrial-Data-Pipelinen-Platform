# Name conventions

## Python (backend, tests, scripts)

We follow [PEP 8](https://peps.python.org/pep-0008/), enforced by Ruff's lint and format rules ([pyproject.toml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/pyproject.toml)).

| Element | Convention | Example |
|---|---|---|
| Modules and packages | `snake_case` | `app/blocks/file_preview.py` |
| Functions, methods, variables | `snake_case` | `resource_path`, `retained_rows` |
| Classes | `PascalCase` | `PipelineDefinition`, `CsvSource` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_READ_BYTES` |
| Private helpers | leading underscore | `_schema_differences` |
| Tests | `tests/test_<feature>.py`, functions `test_<behaviour>` | `test_run_redaction.py` |

## TypeScript and React (frontend)

We follow the [typescript-eslint](https://typescript-eslint.io/rules/) recommended rules and Prettier formatting ([eslint.config.js](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/eslint.config.js)).

| Element | Convention | Example |
|---|---|---|
| Components and their files | `PascalCase` | `RunMonitor.tsx` |
| Other modules | `camelCase` | `projectSelection.ts` |
| Functions and variables | `camelCase` | `parsePreview` |
| Types and interfaces | `PascalCase` | `PreviewResult` |
| Tests | beside the source, `<Name>.test.ts(x)` | `Canvas.test.tsx` |

## API and data

| Element | Convention | Example |
|---|---|---|
| Routes | versioned, plural nouns, kebab or lower case | `/api/v1/projects/{project_id}/pipelines` |
| JSON fields | `snake_case` | `block_version`, `full_row_count` |
| Error codes | `snake_case`, stable | `preview_read_limit` |
| Block identifiers | `<type>.<name>` with a semantic version | `transform.filter` `1.0.0` |
| Database tables | plural `snake_case` | `pipeline_revisions` |
| Environment variables | `LPS_` prefix | `LPS_WORKSPACE_ROOT` |

## Git and GitHub

| Element | Convention |
|---|---|
| Branches | `feature/<issue>-short-name`, `fix/<issue>-short-name`, `spike/<issue>-short-name`, `docs/<issue>-short-name` |
| Commits | Imperative description of the change with the issue number, for example `Reject aliased project folders before reading project data (#37)` |
| Feature labels | `feature:<name>`; iterations are milestones named `Iteration N` |
| Tags | `v0.1.0-iteration1`, `v0.2.0-iteration2`, `v0.3.0-iteration3`, `v1.0.0-release1` on the reviewed commit |
| Architecture decisions | `docs/architecture/decisions/ADR-000N-short-title.md` |
