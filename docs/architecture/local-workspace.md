# Local workspace design — issue #4

The existing `frontend/` React shell and `app/` FastAPI shell remain in place. Repository tools and documentation are not moved. Compose builds the frontend with its npm lock and the API with its hash-verified Python lock. This keeps the application boundaries established by issues #5, #6 and #11.

The browser connects to Nginx on loopback port 3000. Nginx serves the built SPA (including direct navigation) and proxies `/api/` to the API over the internal Compose network. The frontend uses `/api/v1` as its base URL in this build, matching the existing API health route. This avoids hard-coded browser hostnames and CORS changes when the published frontend port changes. Standalone Vite development retains its existing absolute URL configuration.

The API also publishes loopback port 8000 for developer OpenAPI access. Neither service binds a public host interface. A named metadata volume is mounted at `/var/lib/lps`, writable by the non-root API user. This reserves persistent storage for the metadata implementation in issue #7; the current API shell does not create a database. No datasets, credentials, host source directories or Docker socket are mounted into either service. Build contexts use allowlists.

`docker compose down` preserves metadata. Removing volumes is an explicit reset operation. The integration test uses a unique project name and only deletes its own synthetic test volume. It verifies real HTTP health, SPA assets/deep links, versioned API proxying, non-root storage access, persistence after container recreation and teardown. Full ETL acceptance remains Iteration 4 scope.

Alternative considered: browser requests directly to the API's published port. A same-origin proxy avoids a separate CORS/configuration matrix and keeps the frontend build usable with different host ports. Multi-stage builds keep Node and frontend dependencies out of the serving image. The existing Python lock includes development tools; this local development image intentionally reuses that reviewed lock rather than creating a divergent dependency set.

AI assistance: Codex drafted this design, implementation and validation for ham340i's requested issue. Independent student review is pending.
