# Read-only SQL source (#23)

`source.sql` version `1.0.0` reads a local SQLite `.sqlite3` database. It appears
as **SQL Source** in the builder and emits the SDK `table` port for Polars
transforms, including Join. Remote SQL dialects and industrial connectivity are
not implemented or approved by this demonstration.

## Runtime files and references

For manual API execution, each project reads/writes inside
`LPS_WORKSPACE_ROOT/<project UUID>/`. The default root is
`local-data/workspaces`. Configure this on the API process before startup, and
create the project directory with your approved local files. The project UUID
appears in the builder URL. Container users must mount this directory into the
API container explicitly. The portable graph contains only relative resource
references. Traversal and resolution outside the project workspace are rejected.

Direct engine integrations may supply `BlockContext.resolve_resource` to map a
logical reference to an existing file inside `workspace_root`. Local paths and
secret-provider configuration stay in that runtime service. SQLite needs no
password, so no secret value or secret reference is serialized in this block.
The existing private metadata binding model is not a public credential editor.
Timer execution does not yet supply a file workspace; use manual execution for
this example.

## Configuration

```json
{
  "resource_ref": "data.sqlite3",
  "query": "SELECT asset_id, label FROM assets WHERE asset_id = :asset_id",
  "parameters_json": "{\"asset_id\":1}",
  "columns": ["asset_id", "label"],
  "types": ["integer", "string"],
  "nullable": [false, true]
}
```

Use named placeholders and a JSON object of scalar values in `parameters_json`.
Credential keys, nested values, nonfinite numbers and duplicate parameter names
are rejected. Query text and bound values are user-authored portable data; do not
put credentials in either. The form treats Parameters Json as text and the
server validates its contents.

Declare at least one column, in exact query order, with matching type/nullability
lists. Aliases must be unique. Integer, number, string and null values preserve
their SDK types. SQLite does not return native Boolean values; use integer data
and a downstream Cast when needed. BLOBs, invalid values and schema mismatches
fail rather than silently converting. Empty/all-null results preserve the
explicit schema. Timestamps remain strings; date inference is not performed.

## Bounds and failures

Only single SELECT/WITH read queries are accepted. The SQLite connection uses
URI `mode=ro`, `query_only`, and an execution authorizer that rejects writes.
Defaults cap database/result scalar bytes at 16 MiB, rows at 100,000, columns at
256, cells at 1,000,000 and VM instructions at 1,000,000. Limits are configurable
within the published configuration schema. Scalar byte accounting excludes Python
object overhead; this is a bounded local source, not an untrusted-query sandbox.

Connection errors use `sql_connection_failed`; read errors and exhausted query
budgets use `sql_query_failed`; type/order failures use `schema_mismatch`.
The block emits fixed messages without the SQL, bound values, paths or raw SQLite
exception. Correct the local file or configuration and save before rerunning.

## Synthetic join example

The [portable example](examples/sql-join-pipeline.json) contains
CSV → Validate Schema → Filter → Join(SQL) → Aggregate → Parquet. Create these
synthetic resources inside the project workspace:

```python
import sqlite3
from pathlib import Path

# Run from your project's runtime workspace directory.
with sqlite3.connect("data.sqlite3") as connection:
    connection.executescript("""
        CREATE TABLE assets (asset_id INTEGER, label TEXT);
        INSERT INTO assets VALUES (1, 'A'), (2, NULL);
    """)
Path("readings.csv").write_text(
    "asset_id,reading\n1,5\n1,20\n1,30\n2,99\n", encoding="utf-8"
)
```

Save the example definition through the existing project pipelines API, then
open it in the builder and click **Run saved pipeline**. The Parquet result is
`[{"label":"A","total":50}]`; explicit replace policy makes reruns equivalent.
The API integration test executes and verifies this exact output twice.

The builder requires a saved graph and current successful validation before
manual execution. It displays revision, terminal state, timing, row counts,
per-block evidence and log messages, and supports retrying a failed detail read.
Unknown counts remain distinct from measured zero. A request timeout can occur
while synchronous backend execution continues; inspect run history before
starting another expensive run.

Issue #31 remains incomplete: selected-node preview (#26), artifact indexing and
row inspection (#28), the full monitoring/error experience (#30/#33), and nested
quality/aggregate configuration forms are not integrated here. The SQL-only
Playwright scenario authors through the UI; the full graph test uses the API and
engine. Neither test establishes the entire UI acceptance scenario.

See [design](design/issue-23-sql-source.md) and
[verification](testing/issue-23-31-sql-workflow.md).
