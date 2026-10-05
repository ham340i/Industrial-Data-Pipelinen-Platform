# Reproducible local workspace — issue #4

## Prerequisites and layout

Install Git and Docker Desktop (macOS/Windows) or Docker Engine with Compose v2.20+ (Linux). Start Docker before running the commands. Compose supplies Python 3.12, Node 24 and Nginx; host Python/Node are only needed for local tests and source development.

`frontend/` contains the real React workbench; `app/` contains the FastAPI shell. `docker/api.Dockerfile`, `frontend/Dockerfile` and `compose.yml` package those sources. Existing `docs/` and `scripts/` paths remain unchanged. See the [design and tradeoffs](architecture/local-workspace.md).

## Start from a clean clone

```sh
git clone https://github.com/ham340i/Industrial-Data-Pipelinen-Platform.git
cd Industrial-Data-Pipelinen-Platform
# Before merge, check out feature/4-local-workspace.
cp .env.example .env
docker compose config --quiet
docker compose up --build --detach --wait
```

Open http://127.0.0.1:3000. The workbench should show **Local API is connected.** The builder is at http://127.0.0.1:3000/#/builder. API health is available at http://127.0.0.1:8000/api/v1/health and through the frontend at http://127.0.0.1:3000/api/v1/health. OpenAPI documentation is at http://127.0.0.1:8000/docs.

```sh
docker compose ps
docker compose logs --tail=100 api frontend
```

Both services must report healthy. Compose waits for API health before starting the frontend. Sources are copied into images: after editing application code, rerun `docker compose up --build --detach --wait`. There are no host source or dependency mounts.

## Configuration and data

The optional root `.env` only controls `FRONTEND_PORT` (3000) and `API_PORT` (8000). Use free host ports between 1 and 65535. Port 0 requests an ephemeral port for automated testing. All published ports bind to `127.0.0.1`; these defaults are for local development, not public deployment.

The frontend image uses the public build-time value `VITE_API_BASE_URL=/api/v1`. Nginx proxies it to the internal `api:8000` service, so changing host ports requires no application source edits or CORS changes. Standalone frontend development can use the existing absolute URL setting; to reach the actual API use `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1` and run Vite on port 3000, an origin allowed by the API.

The Compose-managed `metadata` volume mounts at `/var/lib/lps`, writable by API UID/GID 10001. `down` and rebuilds preserve it. Issue #7 configures `LPS_METADATA_PATH=/var/lib/lps/metadata.sqlite3`; API startup runs Alembic before serving traffic. The smoke test verifies a real synthetic project row across container recreation. See the [metadata guide](metadata.md) for schema, configuration and backup/reset behavior.

Do not put credentials into `VITE_*` variables; they are visible in browser code. No credentials are needed by these shells. Git ignores local `.env`, secrets, datasets and database files. Docker build contexts allow only required application sources and locks, excluding host secrets, datasets, Git history and local dependencies.

## Stop, restart and reset

```sh
docker compose stop
docker compose start --wait
# Remove containers/network, preserve metadata:
docker compose down
```

For an intentional complete reset of this project's metadata, use `docker compose down --volumes`. This deletes that project's metadata permanently. It does not target other Compose projects. Do not use global Docker prune commands.

## Locked dependencies and base images

Normal builds use `npm ci --ignore-scripts` with `frontend/package-lock.json` and `pip install --only-binary :all: --require-hashes -r requirements.lock`. Every base image is pinned by manifest digest so builds do not silently switch runtime images.

For an intentional frontend dependency update, use Node 24 and npm 11:

```sh
cd frontend
npm install --package-lock-only --ignore-scripts
npm ci --ignore-scripts
npm run check
```

For an intentional backend dependency update, edit `requirements.txt` or `requirements-dev.txt`, then use uv:

```sh
uv pip compile --universal --generate-hashes --python-version 3.12 requirements-dev.txt -o requirements.lock
```

Review lock diffs and commit them with the dependency change. Run the backend checks in the [developer guide](getting-started.md#backend-validation). To refresh base images, pull the documented tags, inspect their `RepoDigests`, update the Dockerfile digests and rerun the full smoke test. Do not hand-invent dependency hashes or remove hash verification.

## Integration verification

With host Python 3.11+:

```sh
python3 scripts/smoke_workspace.py
```

For the real browser test, additionally use Node 24, install the locked frontend dependencies and Chromium:

```sh
cd frontend
npm ci --ignore-scripts
npm run browser:install
cd ..
python3 scripts/smoke_workspace.py --browser
```

The test creates a unique Compose project, chooses ephemeral loopback ports, builds both images, checks HTTP health, asset serving, SPA fallback, real browser connectivity (with `--browser`), non-root storage writes and persistence after container recreation. Its `finally` cleanup removes only the test project's containers/network and synthetic volume. Existing developer metadata is untouched. CI runs the browser variant on a clean checkout under **Compose workspace smoke**.

Full pipeline execution is outside this shell/workspace issue. See the [actual validation record](testing/issue-4-local-workspace.md) for results and review status.

## Troubleshooting

| Symptom | Action |
|---|---|
| Cannot connect to Docker daemon | Start Docker Desktop or the Linux Docker service; wait for `docker info` to succeed |
| Port already allocated | Change the corresponding root `.env` port and rerun `docker compose up --detach --wait` |
| Unhealthy API/frontend | Inspect `docker compose logs --tail=100 api frontend`; verify registry access and rebuild |
| npm engine warning in host tests | Use Node 24; containers already supply it |
| Registry/network or hash failure | Check network/proxy settings; retain hash verification and investigate the lock before changing it |
| Metadata missing after reset | `down --volumes` intentionally deletes it; ordinary `down` preserves it |
