# Configuration form validation and rendering

The builder configuration panel reads the selected block's public registry schema.
Schema validation converts supported definitions into fields. Value validation
applies defaults and checks the current configuration. The form combines those
results with server diagnostics, then renders each control. See [issue #130](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/130).

## Design decision

Separate schema validation by rule and value type. Separate field control rendering
from the form's state, diagnostics, and focus handling. Keep the same schema
interpretation, first-error order, input controls, and public-data checks. The
backend retains authority over validation before execution.

A general-purpose JSON Schema validator would add a dependency and could change
the accepted schema subset or the error contract. A table of control factories
would obscure the distinct editing semantics of JSON, select, and scalar fields.
Named validators and React components keep these differences explicit.

## Enforcement and verification

- ESLint checks production frontend functions for a maximum complexity of 15
  and a maximum of 50 lines, excluding blank lines and comments. Existing
  violations outside this issue have a checked-in baseline. Remove the relevant
  baseline entries as those functions are refactored.
- The configuration schema and panel are checked without baseline suppressions.
  The two local length exceptions keep the focusable form and the registry-backed
  sidebar together. Their complexity is still checked.
- Existing tests exercise schema acceptance and rejection, typed defaults, invalid
  edits, recovery, field focus, save and reopen, and real API execution.
