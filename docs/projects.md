# Local projects — issue #19

The workbench can create, list and reopen SQLite-backed projects. Start the
workspace using [Compose](local-workspace.md) or the
[standalone developer setup](getting-started.md).

## Using projects

1. Open Projects, enter a name and choose Create project (or press Enter).
2. The saved project opens its builder workspace. This story reserves a workspace
   for that project; the visual editor and pipeline save/reload are later work.
3. Return to Projects and select an Open link to reopen a project. Lists show
   twenty projects per page, with Previous/Next controls.
4. Use Builder or Resume last project to restore the most recently opened project.
   A direct link also survives reload. API availability is needed to confirm it.

Project metadata survives API restarts and ordinary `docker compose down`.
The selected project ID is remembered in browser localStorage; clearing it or
changing browser origins/API URLs removes that association, not the project.
If storage is blocked, direct URL navigation works but browser-session
restoration is unavailable. Missing projects offer Choose a project; transient
API failures offer Retry. Server payloads are never displayed as raw errors.

Draft pipeline names are unsaved. They persist through navigation within the
same project, but clear on refresh or switching project identity. Clearing a
draft keeps the current project. No pipeline data is saved by this feature.

## API contracts

| Method/path | Response |
|---|---|
| POST `/api/v1/projects` | 201 with saved project |
| GET `/api/v1/projects?offset=0&limit=20` | 200 with page metadata and project items |
| GET `/api/v1/projects/{project_id}` | 200 with project; 404 if a valid ID is absent |

Create body: `{"name":"Synthetic inspection"}`. Public project fields are
`id` (UUID), `name` and `created_at` (UTC ISO-8601 timestamp). Page fields are
`items`, `total`, `offset` and `limit`. Names are trimmed, 1–128 characters,
without control characters. Unknown body fields are rejected; duplicate names
are allowed with different IDs. Names are display labels and never filesystem
paths. Invalid IDs/body/query parameters return the existing structured 422
envelope; missing projects return `project_not_found` with a correlation ID.

Limits are 1–100; offsets are nonnegative. Ordering is creation time descending,
then ID ascending. Concurrent inserts can shift offset pages. The UI validates
actual response JSON at runtime and does not assume TypeScript proves its shape.

Projects remain local and unauthenticated under the existing loopback deployment
model. This introduces no enterprise sharing or remote access policy. Workspace
bindings, pipeline revisions and secret references are excluded from responses.

## Tests and boundaries

Backend tests use real temporary SQLite files, including an API restart. UI tests
use synthetic HTTP mocks and exercise loading, creation, validation, retry,
pagination, keyboard opening, storage recovery and draft isolation. The Compose
browser test creates/reopens a real project and restores its ID in a fresh
browser context. The smoke script checks reopening through the actual HTTP API
after container recreation and cleans up only its synthetic volume.

See [ADR-0005](architecture/decisions/ADR-0005-local-projects.md),
[tests](../tests/test_projects.py),
[UI tests](../frontend/src/Projects.test.tsx), and
[observed results](testing/issue-19-local-projects.md).

AI Assistance: Codex implemented and tested the feature at Karim's instruction;
independent review and stakeholder acceptance remain pending.
