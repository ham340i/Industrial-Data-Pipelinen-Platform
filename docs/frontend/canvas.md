# Visual pipeline canvas (#15)

Open Builder, optionally within a project. The block library loads from `GET /api/v1/blocks`; search by name, category or block ID. Each entry shows its exact version and input/output port kinds. Drag an entry onto the canvas or focus its Add button and press Enter. Pan the background and use the zoom controls. Click a node to select it; drag it or focus it and use arrow keys to move it. Delete selected removes the selected node and its incident edges. Selected edges can also be removed with Delete.

Connect an output handle to an input handle. The editor rejects unknown or incompatible ports, duplicate connections, multiple connections to single inputs, self-connections and cycles. Rejected connections leave the graph intact and display a reason. These are authoring checks; backend validation before execution remains authoritative.

## Pipeline check (#21)

The Pipeline check panel above the canvas asks the API whether the current draft can run, shortly after each change to blocks, connections or configuration. Moving or selecting nodes does not trigger a check. Problems appear in three places: as a list in the panel (click one to select its node), on the affected node with a red outline and message, and on the affected connection in red. **Run pipeline** is enabled only when the latest check matches the graph on screen and found no problems. Checking never changes the draft. Fix the listed problem and the panel updates. See the [design](../architecture/graph-validation.md).

The library offers the registered production triggers, sources, transforms, quality checks and sinks. Register new implementations in `app/blocks/catalog.py`; the library needs no corresponding hardcoded frontend cards. Configuration defaults come from public schema metadata. Select a node to edit its typed fields in the [configuration panel](block-configuration.md). Current backend field messages are shown beside inputs; selecting a configuration problem focuses its field.

The catalog's `library_visible` flag controls new authoring choices and defaults to `true`. Synthetic Add Constant sets it to `false`: it is absent from browsing, search and add/drag choices. Its source remains in `app/blocks/sample.py` as a developer example. The API still returns its metadata, and saved pipelines using `synthetic.add_constant@1.0.0` retain their names, ports, editable configuration, connections and runtime resolution. Hiding a block does not delete or migrate saved nodes, disable execution, or act as an authorization boundary. Older API responses without this flag remain visible.

For a production block with numeric configuration, add **Row Count** and edit **Min Rows** (zero or greater). It requires an upstream table; an unconnected Row Count node correctly reports a missing-input problem.

Drafts live in memory across route navigation within a project. Use Save pipeline in a project to persist the name, configuration, graph and layout. Changing the name and saving renames the existing pipeline. Open a saved pipeline to restore it; confirm before replacing unsaved edits. Save a copy requires a different name. Revision conflicts retain the draft so you can save a copy or open the latest version. Export JSON downloads the last saved current graph. Refreshing, changing projects or Clear draft discards unsaved edits. The graph serialization helper produces the existing version-1 definition with stable node/edge IDs, block IDs/versions/configuration and separate layout positions. UI selection and measurement state are excluded.

## Selected-node preview (#26)

In a project, select CSV, JSON or Parquet Source, or Select Columns on a supported file-source path, and use **Preview selected node** below the canvas/configuration area. Choose row/cell limits and inspect Sample, Schema or Null summary. CSV/JSON full counts remain unknown until input completion is observed; Parquet full counts are labeled as reported by file metadata. JSON schema inference is explicitly sample-scoped. Null counts describe only returned rows. Changes to the selected node, semantic draft, project, output or limits discard old results. Refresh is explicit. Unsupported blocks explain their limitation; failures retain the draft and can focus an affected configuration field. SQL preview is excluded from this extension.

The API needs a configured workspace and project data folder. Use **Settings** in the sidebar or **Configure workspace** on a setup error to save a root and prepare project folders. The app setting overrides the environment fallback. See [workspace settings](../architecture/workspace-settings.md) and [supported paths and budgets](../architecture/selected-node-preview.md). The library scrolls inside its panel to keep preview accessible even with many registered blocks.


## Error recovery (#33)

Preview errors offer **Configure node** only for a node in the submitted graph.
The action focuses its affected field when supplied, otherwise the configuration
region. Editing, changing selection or opening another pipeline discards old
preview errors. Retry, cancellation and completion preserve keyboard focus
without moving it away from a field the user has started editing.

**Run saved pipeline** requires a saved, unchanged, currently valid graph. It
sends that saved revision as a precondition, so a teammate's newer save causes a
conflict instead of executing a different revision. Open the latest version or
save a copy to resolve the conflict; neither recovery overwrites the current
draft automatically. Runtime failures offer **Configure failed block** while
the result still matches the saved revision and semantic graph. After an edit,
old evidence is labeled separately and its configuration links disappear.

**Retry run results** repeats only the result read, never the execution. If the
execute response is lost or malformed, a run may already exist; check run
history before starting another. Configuration recovery does not save or rerun
anything. See [design and integration boundaries](../architecture/error-recovery.md)
and [verification](../testing/issue-33-validation-recovery.md).

## Verification

Run `npm run check --prefix frontend`, followed by `npm run test:browser --prefix frontend` with Chromium installed. Run the backend suite using the developer guide. The real API suite (`npm run test:standalone --prefix frontend`) uses production blocks for creation, configuration and connections, and separately checks reopening an existing hidden example. See the [library cleanup verification](../testing/block-library-visibility.md) for current evidence and the [iteration evidence](../iterations/iteration-2/testing-evidence.md) for historical results.
