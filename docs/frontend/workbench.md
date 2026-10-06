# Frontend workbench guide

Implements the bounded frontend scope of [issue #5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5). The backend, project persistence, graph editor and execution engine remain separate work. No production or stakeholder acceptance is claimed.

## Install and run

Use Node.js 24 and npm 11. From the repository root:

```sh
cd frontend
npm ci --ignore-scripts
npm run dev
```

Open http://127.0.0.1:3000. The server binds to loopback and uses strict port selection so it cannot silently move to an origin rejected by the API. No backend or credentials are required to navigate the shell. To connect the real backend, follow the [developer guide](../getting-started.md#backend-validation).

```sh
npm run check
npm run test:watch
npm run build
npm run preview
```

`check` runs ESLint, Prettier validation, strict TypeScript, Vitest and the production build. Build output is in `frontend/dist/`; preview serves it locally on port 3000, matching the backend's allowed origins. Preview is a verification server, not a production deployment. Commit package.json and package-lock.json together; use `npm ci --ignore-scripts` in clean environments. `npm run test:standalone` starts real API/Vite services and checks browser connectivity; see the [standalone smoke guide](../getting-started.md#real-standalone-connection-smoke).

## Use the workbench

- Overview explains the foundation and checks the local API. Retry performs another request after a failure.
- Projects shows an explicit placeholder because project storage is not implemented. It does not claim that an unqueried database contains zero projects.
- Builder reserves the editor route. Its draft name remains while navigating within this tab; Clear draft resets it. Refresh loses the draft. Graph operations and saving are unavailable.
- Tab reaches the skip link and navigation. Enter activates links. Route changes move focus to the main content and update the document title. Unknown routes offer a link home.

Hash URLs such as `/#/builder` support direct entry, refresh and browser history without server rewrites.

## Configuration and provisional API contract

Optional: copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_BASE_URL`. Default: `http://127.0.0.1:8000/api/v1`. A bare HTTP(S) host also receives the `/api/v1` prefix; an explicit path prefix is preserved. Restart Vite after changing it; production values are embedded at build time. Credentials, query strings and fragments are rejected. Every `VITE_*` value is public: never add passwords or tokens.

The frontend requests `GET <base URL>/health` with HTTP 200 and JSON `{"status":"ok"}`. Additional fields are ignored. Other shapes produce an API compatibility warning. Its default now matches the `/api/v1/health` route implemented in issue #6; run standalone Vite on port 3000. Compose sets the supported same-origin base `/api/v1` and proxies requests to the API; see the [workspace guide](../local-workspace.md). The backend must allow the actual frontend origin via CORS (127.0.0.1 and localhost are different origins). The client does not send cross-origin cookies.

Requests time out after 10 seconds. Errors are classified as network, timeout, HTTP, invalid-response or unknown; raw response bodies, server stack traces and request configuration are not shown. Cancellation stays recognizable to TanStack Query. Health results are fresh for 30 seconds; automatic retries and focus refetch are disabled to avoid noisy offline traffic. The cache is in memory.

## Code map and extension rules

| Location | Responsibility |
|---|---|
| `frontend/src/App.tsx` | MUI shell, navigation, placeholders and health feedback |
| `frontend/src/api/client.ts` | Public configuration, Axios transport and safe error normalization |
| `frontend/src/api/health.ts` | Runtime health validation and TanStack Query hook |
| `frontend/src/state/editor.ts` | Ephemeral draft and selection state only |
| `frontend/src/test/` | Synthetic HTTP mock server and test cleanup |

Keep remote data in query hooks and editor-only state in Zustand. Add runtime validation for each new response contract. Do not store credentials or raw industrial datasets in browser storage. Integrate the future graph editor behind the builder route without coupling execution to React. See [ADR-0001](../architecture/decisions/ADR-0001-workbench-shell.md).

## Browser smoke tests

After building, install Playwright Chromium and run the production-shell tests:

```sh
cd frontend
npm run browser:install
npm run test:browser
```

CI installs Chromium with its Linux dependencies using the locked local Playwright executable. Dependency lifecycle scripts are disabled during npm installation; the build uses packaged native binaries. To use an existing local Chrome, set `PLAYWRIGHT_CHROME_PATH` to its executable path when running the command. The suite starts and stops a loopback preview server on port 4173; keep that port free. These are shell smoke tests with synthetic health responses, not full ETL end-to-end acceptance. Screenshots and failure traces are written to ignored `frontend/test-results/`.

## Tests and troubleshooting

Tests use MSW at the HTTP boundary and isolated query clients. They cover pending/success/failure/retry rendering, malformed payloads, timeout, cancellation, configuration validation, keyboard navigation, route recovery and draft lifecycle. No live backend is stubbed into a claimed end-to-end release test. Full engine/API Playwright acceptance remains iteration 4 work.

| Symptom | Action |
|---|---|
| Offline API warning | Start the backend when available; verify the configured address and CORS origin, then Retry |
| Unsupported health response | Reconcile the backend schema with the provisional contract |
| Blank page after configuration change | Inspect the browser console for configuration errors; use the safe example URL and restart Vite |
| npm engine error | Use Node 24 and reinstall with npm ci --ignore-scripts |
| Port already occupied | Stop the service occupying port 3000, or explicitly choose another port and update backend CORS for that origin. Vite will not silently select a different port. |
| Draft disappeared on refresh | Expected: this iteration has no persistence |

## Security, performance and review limits

The shell uses no analytics, remote fonts, credentials or persistent browser storage. It contacts the configured API for health only. Dependency security should be rechecked during upgrades. React and MUI vendor chunks are separated from application code for browser caching; no dataset rendering or execution workload has been benchmarked. Keyboard behavior is automated, but assistive-technology and real-backend acceptance require human review. See [verification evidence](../testing/issue-5-workbench.md).
