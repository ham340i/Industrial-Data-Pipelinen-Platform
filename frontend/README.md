# Local Pipeline Studio frontend

React 19 workbench foundation for issue #5. See the [complete guide](../docs/frontend/workbench.md), [design decision](../docs/architecture/decisions/ADR-0001-workbench-shell.md) and [verification](../docs/testing/issue-5-workbench.md).

Use Node 24 and npm 11:

```sh
npm ci --ignore-scripts
npm run dev
npm run check
npm run preview
```

The API is optional for navigating the shell. Project persistence, the graph editor and pipeline execution are future scope.

The builder can run the latest saved, validated graph and display run evidence.
See [SQL source and workspace setup](../docs/sql-source.md). Run
`npm run test:release` with the backend Python interpreter in `LPS_PYTHON` for
an isolated, real SQL author/save/open/run/rerun/failure browser test. This does
not establish the complete #31 preview/artifact acceptance scenario.
