# Block configuration (#17)

Select a node in Builder to edit its exact block version. The configuration panel
appears beside the canvas on wide screens and below it on smaller screens.
The canvas retains its full height in the narrow-screen column layout.
Controls are labelled from the public registry's `config_schema`; no block IDs or
field lists are hardcoded in the form.

Changes belong to that node's `data.config`. Selecting another node does not move
or erase values. Save pipeline within a project to persist them, then Open to
restore them after refresh. Export JSON includes the same configurations.
Unsaved edits follow the existing draft lifecycle: Clear draft, project switch,
or refresh discards them. A failed save keeps the edited draft.

## Supported controls and feedback

- Strings, finite numbers, integers, booleans and scalar enum choices.
- Nullable scalar fields, with an explicit null action/choice.
- Scalar lists, entered as JSON, with item type, length and uniqueness checks.
- Required fields, numeric bounds, string lengths and fixed scalar values.

Defaults come from the SDK schema. Empty or unfinished number/list edits stay
editable, including across node selection. They can make the configuration
invalid; saving a draft is separate from execution readiness. The backend
remains authoritative and Run stays gated by its current validation report.

Local errors identify the block and field. Current backend field errors appear
beside the matching input; errors for another node or an old graph do not.
Click a problem in Pipeline check to select its node and focus its field when
available (or its first control for a block-level problem). Nested list-item
diagnostics are attached to the list control.

Loading and failed registry requests preserve values. Retry definitions reloads
metadata. Missing/duplicate exact versions, unsupported schemas, and malformed
registry responses produce visible alerts rather than guessing controls.
Nested objects, nested arrays, schema references, patterns and arbitrary unions
are outside this bounded Release 1 subset. No configuration fields is a valid
empty form. Editing is disabled while the existing persistence operation runs.

## Public configuration boundary

Use logical resource IDs such as `resource_ref`; do not enter credentials or
absolute machine paths. The editor rejects known credential/runtime field names,
non-finite/non-JSON values and absolute paths, including unsafe registry defaults.
Unsafe imported configuration is preserved but not rendered by the form. These
checks deliberately align with the backend portability boundary and are not an
arbitrary-secret detector: a generic string cannot be proven non-secret. Runtime
resource binding remains separate work.

## Design and verification

The existing registry query cache is shared with the canvas. A single existing
graph store owns configuration and serialization; there is no second config map
or replacement graph format. `fieldMessages` reuses the merged #21 diagnostic
contract. No API endpoint, database migration or dependency was added.

See [acceptance and execution evidence](../testing/issue-17-configuration.md).
The real-API browser spec covers distinct node values, invalid configuration,
save/reopen, JSON export, a failed duplicate-name copy and narrow-screen editing.
Full execution and the
Iteration 4 workflow remain separate work; a production source block is not
invented to make the current synthetic catalog runnable.
