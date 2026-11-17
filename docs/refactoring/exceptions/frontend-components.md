# Documented exception: frontend component and parser size

Recorded November 17, 2026 for Release 1. Related work item: [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36).

## What does not meet the limits

Measured with ESLint's `max-lines-per-function` (50) and `complexity` (15) rules over `frontend/src`, excluding tests.

| File | Function | Lines | Complexity |
|---|---|---:|---:|
| `RunControls.tsx` | `RunControls` | 230 | 42 |
| `configuration/BlockConfigPanel.tsx` | `ConfigForm` | 249 | 27 (inner field renderer) |
| `App.tsx` | `App` | 188 | within limit |
| `Canvas.tsx` | `GraphCanvas`, `BlockCard` | 176, 85 | within limit, 16 |
| `PipelineControls.tsx` | `PipelineControls` | 169 | 25 |
| `Projects.tsx` | `Projects` | 168 | 17 |
| `WorkspaceSettings.tsx` | `WorkspaceSettings` | 148 | 25 |
| `PreviewPanel.tsx` | `Results`, `Session`, `Controls` | 141, 94, 76 | within limit, 17, within limit |
| `ValidationPanel.tsx` | `ValidationPanel` | 118 | within limit |
| `api/preview.ts` | `parsePreview` | 100 | 53 |
| `api/runs.ts` | `parseRun`, `executePipeline` | 69, 64 | 38, 25 |
| `api/pipelines.ts` | `parseDefinition` | 53 | 34 |

Other components exceed 50 lines by smaller margins. No frontend source file exceeds 500 lines of code.

## What is justified, and why

**Line count of component functions.** A React function component's body is mostly declarative JSX. One form with labelled, accessible controls is many lines of markup with no branching. Splitting that markup into child components only to satisfy a line count would spread one screen's layout across files and add props that exist only to pass state back down. We treat the 50-line limit as applying to logic, and judge components by complexity instead.

## What is not justified

The complexity figures above are real and are not defended here:

- `parsePreview`, `parseRun` and `parseDefinition` validate an API payload field by field in one function. They should be composed from small per-field guards, as [api/guards.ts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/api/guards.ts) already does for simple cases.
- `RunControls`, `PipelineControls`, `WorkspaceSettings` and `ConfigForm` mix request state, derived status text and rendering. The state handling belongs in hooks and the per-field rendering in child components.

These were not refactored for Release 1 because the end-to-end browser workflow that would catch regressions in them ([#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31)) is not merged yet. Refactoring user-interface state without that safety net on the release date was judged a larger risk than carrying the debt for one iteration. The backend, which has full test coverage, was brought within all three limits.

## Plan

Refactor the parsers first (pure functions with existing unit tests), then the four components after [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) merges. Add the two ESLint rules as warnings, then as errors once the list above is empty.
