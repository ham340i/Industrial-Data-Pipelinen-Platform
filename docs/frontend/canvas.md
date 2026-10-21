# Visual pipeline canvas (#15)

Open Builder, optionally within a project. The block library loads from `GET /api/v1/blocks`; search by name, category or block ID. Each entry shows its exact version and input/output port kinds. Drag an entry onto the canvas or focus its Add button and press Enter. Pan the background and use the zoom controls. Click a node to select it; drag it or focus it and use arrow keys to move it. Delete selected removes the selected node and its incident edges. Selected edges can also be removed with Delete.

Connect an output handle to an input handle. The editor rejects unknown or incompatible ports, duplicate connections, multiple connections to single inputs, self-connections and cycles. Rejected connections leave the graph intact and display a reason. These are authoring checks; backend validation before execution remains authoritative.

The catalog exposes explicitly registered SDK blocks. Currently it contains Synthetic Add Constant, an SDK example, not a production ETL block. Register future implementations in `app/blocks/catalog.py`; the library needs no corresponding hardcoded frontend cards. Configuration defaults come from public schema metadata. Schema-driven configuration editing is owned by #17.

Drafts live in memory across route navigation within a project. Use Save pipeline in a project to persist the name, configuration, graph and layout. Changing the name and saving renames the existing pipeline. Open a saved pipeline to restore it; confirm before replacing unsaved edits. Save a copy requires a different name. Revision conflicts retain the draft so you can save a copy or open the latest version. Export JSON downloads the last saved current graph. Refreshing, changing projects or Clear draft discards unsaved edits. The graph serialization helper produces the existing version-1 definition with stable node/edge IDs, block IDs/versions/configuration and separate layout positions. UI selection and measurement state are excluded.

## Verification

Run `npm run check --prefix frontend`, followed by `npm run test:browser --prefix frontend` with Chromium installed. Run the backend suite using the developer guide. New tests cover discovery, keyboard add/delete, connection constraints, graph serialization and the registry endpoint. See the [iteration evidence](../iterations/iteration-2/testing-evidence.md) for actual execution status.
