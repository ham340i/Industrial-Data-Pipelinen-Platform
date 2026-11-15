# Governed artifacts and bounded queries

Issue [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28)
links successful CSV and Parquet sink publications to their producing run and
immutable pipeline revision. The implementation is local-first: metadata is in
SQLite and artifact bytes remain beneath the configured workspace root.

## Configuration

`LPS_WORKSPACE_ROOT` selects the private local workspace. Its default is
`local-data/workspace`. Immediate and timer execution publish sink files under
`<root>/<project id>/<resource_ref>`, and artifact queries resolve the stored
logical resource reference inside that same project folder (aligned by the
issue #37 integration matrix; previously the query looked beneath the bare
root and reported every executed artifact as unavailable). API
clients never submit or receive a resolved machine path.

## Metadata endpoint

`GET /api/v1/artifacts/{artifact_id}` returns the artifact ID, logical
`resource_ref`, format, row count, declared schema, producing run, pipeline and
pipeline revision, node and publication time. Migrated legacy records remain
readable with `data_schema: null`; they are not queryable until a real schema is
available.

## Query endpoint

`POST /api/v1/artifacts/{artifact_id}/query` accepts only this shape:

```json
{"columns":["name","value"],"offset":0,"limit":100}
```

`columns` is an optional projection from the registered schema. An empty list
selects all registered columns when there are at most 100. Limits are 500 rows,
100 columns, 50,100 fetched cells including the one-row pagination look-ahead,
and offset 1,000,000. The response contains column names, row arrays,
provenance IDs and `has_more`.

There is no SQL field and no path field. Only a registered Parquet artifact ID
can reach DuckDB. CSV metadata is discoverable but CSV queries are rejected.
Unknown columns, missing files, unsafe stored references and unsupported result
values produce stable error envelopes without disclosing local paths.

## Example

```powershell
$body = @{ columns = @("name"); limit = 25 } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/artifacts/ARTIFACT_UUID/query `
  -ContentType application/json -Body $body
```

See the [design](architecture/artifact-governance.md) and
[verification record](testing/issue-28-artifact-query.md).
