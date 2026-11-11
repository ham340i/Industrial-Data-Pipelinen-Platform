# MarcElHaddad1 – Iteration 3

Period: Iteration 3. Status: local work in progress; no PR, independent approval,
merge or hosted CI is claimed.

## Summary

Implemented Issue [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28):
durable artifact provenance and bounded registered-Parquet queries through
DuckDB. The work connects successful sink publication to run/revision metadata
and exposes safe metadata/query APIs without raw SQL or client paths.

## Engineering design and implementation

- Extended `OutputEndpoint` with the declared schema and migration-safe legacy
  backfill.
- Registered only completed production file-sink artifact frames in the final
  run transaction and retained real consumed row counts.
- Implemented artifact-ID resolution, shared workspace containment, registered
  column projection, parameterized path/limit/offset, and strict result bounds.
- Added metadata/query endpoints, stable errors and configured workspace use for
  immediate and timer execution.
- Used PyArrow for typed Parquet publication and DuckDB for direct bounded scans;
  the service does not load the complete dataset into Python.

Design: [artifact governance](../architecture/artifact-governance.md). Usage:
[artifact API](../artifacts.md).

## Tests and evidence

Added registration, query-policy, API and real executor → metadata → DuckDB
integration tests. I manually ran the focused checks and the complete 720-test
backend suite. Hosted-CI evidence remains pending. See the [verification
record](../testing/issue-28-artifact-query.md).

## Reviews

Reviewed and approved the corrected Issue #25 PR #71 before beginning this
work. Issue #28 independent review by the assigned teammate is pending.

## Problems solved and learning

The regenerated dependency set uses Starlette's maintained `httpx2` test
transport; retaining legacy `httpx` caused TestClient requests to stall.
The artifact query path also required separating logical resource identity from
resolved machine paths and distinguishing legacy unknown schema from invalid
new metadata.

## AI assistance

Tool: Codex. I explained Issue #28, the required behavior and what needed to be
done. Codex implemented the code, tests and documentation at my direction. I
then manually ran the focused and full verification commands and checked their
results. This record does not claim unaided authorship or completed teammate
review.
