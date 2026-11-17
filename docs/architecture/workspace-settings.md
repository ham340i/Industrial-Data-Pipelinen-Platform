# Workspace settings

Open **Settings** in the sidebar to configure the file workspace used by selected-node previews. A **Configure workspace** link also appears on preview setup errors. The route is `/#/settings/workspace`.

## Setup

1. Create a parent data folder on the computer running the API.
2. Choose **Browse** beside **Workspace root folder** to open the native Windows File Explorer folder-selection dialog. Navigate to a folder and choose **Select folder**. Cancelling leaves the field unchanged. Choose **Save workspace** to validate and apply the selection; selecting a folder alone does not save it. You can also enter an absolute path directly.
3. Save checks access and creates `<root>/<project UUID>/inputs` for every existing project. New projects receive the same folder structure automatically.
4. Put input files in the project's folder and configure a source with a relative Resource Ref such as `inputs/readings.json`.
5. Return to the project builder and explicitly preview again. Navigation through Settings preserves the draft in the current tab; refreshing the browser still discards unsaved drafts.

The setting refers to the API computer's filesystem. Native Browse requires the API to run on the same Windows desktop as the user and a loopback connection. On remote/container or non-Windows deployments, enter an available folder path manually. Remote selections remain restricted to configured workspace roots and their subfolders. The picker uses Windows IFileOpenDialog with FOS_PICKFOLDERS and returns an absolute filesystem path; it does not upload files.

Changing the root does not move or delete data, change portable pipeline definitions or rewrite existing private resource bindings. Absolute bindings must still fall inside the selected project's new root. Failed saves leave the old setting active, although empty directories prepared before a failure may remain. Root changes affect subsequent preview requests; an already running preview keeps its captured root.

## Persistence and precedence

- A saved app setting takes precedence over `LPS_WORKSPACE_ROOT`.
- Without an app setting, the startup environment supplies the root.
- **Use environment setting** removes the app override. An environment root is validated and its project folders are prepared before switching back; with no environment root, preview becomes unconfigured.
- Changes apply immediately and survive API restarts. The environment itself and `.env` are not rewritten.

The private setting is stored atomically in `<metadata filename>.workspace.json`, alongside the configured metadata database. For the default installation this is `local-data/metadata.sqlite3.workspace.json`. Keep this file private and back it up with the installation configuration. Separate metadata database filenames have separate settings files. A corrupt settings file produces a repairable error instead of silently switching roots.

Preview, manual execution, timer ticks and artifact queries use the effective workspace selection. Each operation captures its root when it begins; changes do not redirect operations already running. This reconciles workspace selection with the execution/artifact features merged from `main`. Existing artifact files are not relocated: queries can report an artifact unavailable after a root change until the original root is restored.

## API and implementation

`GET /api/v1/settings/workspace` reports `root_path`, `source` (`application`, `environment`, or `unconfigured`), `ready`, an explanatory `message`, and `allowed_roots`. `ready` describes root availability; Save performs the actual read/write probe and prepares project folders.

`PUT /api/v1/settings/workspace` accepts `{"root_path":"<absolute API-computer folder>"}` or `{"root_path":null}` to restore the environment. Roots must already exist. Access probes use temporary files removed immediately. Missing roots, files in place of directories, inaccessible folders and aliased project folders produce safe structured errors. Settings responses and errors use `Cache-Control: no-store`.

`POST /api/v1/settings/workspace/pick-folder` accepts `{"initial_path":"<optional folder>"}` (or null/omitted initial_path). It opens the native Windows folder picker and returns `{"path":"<selected folder>"}` or `{"path":null}` on cancellation. It does not create folders or save settings. Only one picker can be open at a time. The helper runs in an isolated COM STA process with its console hidden and a five-minute timeout; the frontend waits for selection and disables duplicate actions. Remote/non-Windows clients receive an actionable manual-entry fallback. Responses and errors use `Cache-Control: no-store`.

Native selection and unrestricted local saving require both a loopback client address and a loopback request hostname. Browser requests must come from a configured workbench origin or the same origin; cross-site requests without Origin are rejected. Forwarded host/client headers do not grant local access. Remote manual selections remain contained inside startup-configured roots and their descendants. Paths are checked lexically before filesystem probes; traversal and directory links/junctions below the trusted root are rejected. Arbitrary UNC/device paths cannot trigger probes unless a startup-configured root explicitly permits them. Private settings already saved on disk remain trusted installation configuration. Protect the API and private sidecar from untrusted writers.

`app/workspace.py` owns validation, persistence, folder preparation and the API. `app/native_folder_picker.py` bridges to the Windows Common Item Dialog without additional dependencies. `app/projects.py` prepares new project folders; a preparation failure rolls back project creation. The React settings screen and typed API client live in `frontend/src/WorkspaceSettings.tsx` and `frontend/src/api/workspace.ts`. No database migration was added.

## Verification

Native picker tests cover selection without implicit saving, cancellation, invalid initial paths, local/remote and origin checks, unsupported platforms, concurrent requests, helper errors/timeouts and persistence after Save. Frontend tests verify native request dispatch, cancellation, explicit saving and manual-entry fallback. The browser scenario stubs only the OS dialog response and uses the real API for saving; Windows dialog behavior is checked separately on the desktop.

Feature tests cover immediate preview switching, persistence through a fresh database instance, environment precedence/reset, new project folders, invalid/inaccessible paths, atomic-save failure, existing-file preservation, corrupt-setting repair and no-store errors. Frontend tests cover successful save/reset, validation errors and recovery from load errors. The real-API browser scenario checks the preview-to-settings-to-builder flow, unsaved edits, persisted configuration, desktop/mobile layout and a successful preview after setup.

Local verification on 2026-11-11: 792 backend tests passed (including 11 workspace-settings cases), 127 frontend tests passed across 17 files, and five real-API browser scenarios passed (workspace setup, CSV/JSON/Parquet previews and pipeline save/reopen). Mypy checked 86 Python files; Ruff, frontend lint, TypeScript, production build, documentation/repository checks and diff whitespace checks passed. The test environment used Python 3.13.1 and Node 24 on Windows; Python 3.12 CI is not claimed. Existing deprecation warnings, transient React Flow resize warnings and one Windows connection-reset warning did not fail tests. Desktop and 390 px screenshots were inspected.

Reproduce with the development interpreter using `python -m pytest -p no:cacheprovider --basetemp <fresh-temporary-directory>`, `python -m mypy`, and, from `frontend/` with Node 24, `npm test`, `npm run lint`, `npm run build`, and `npm run test:standalone -- workspace.spec.ts preview.spec.ts pipelines.spec.ts`. Browser verification used isolated metadata/data and ports 8001/3001 via the local test override, leaving the user's API and workspace configuration unchanged.

OpenAI Codex implemented and verified this user-requested feature. Local test results are separate from CI or independent review acceptance.
