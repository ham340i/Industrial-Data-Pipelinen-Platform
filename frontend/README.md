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
