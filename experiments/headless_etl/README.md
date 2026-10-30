# Issue #10: headless ETL proof

This bounded spike executes a portable DAG through the existing versioned Block
SDK: CSV source → Select Columns → Parquet sink. It uses synthetic local data,
no UI, API or database. Blocks are registered explicitly under `spike.*` IDs;
they are not advertised as production blocks in the workbench.

Design: the DAG is validated before execution, then nodes run sequentially in
its deterministic topological order. Edges route SDK table payloads by port.
Resource names in JSON resolve through runtime context; machine paths never enter
the definition. CSV columns have an explicit string schema (empty cells stay
empty strings). Polars selection preserves row order and requested column order.
Parquet uses an explicit Arrow schema, including for zero rows. Output is created
exclusively so an existing artifact is never overwritten; failed writes remove
the incomplete artifact. SDK lifecycle events and safe node errors are retained.

Run from the repository root with Python 3.12+:

```sh
python -m pip install --only-binary :all: --require-hashes -r requirements.lock
python -m pip install --only-binary :all: --require-hashes -r experiments/headless_etl/requirements.lock
python -m experiments.headless_etl.spike
python -m pytest experiments/headless_etl/test_spike.py
```

The demo writes only inside a temporary directory, reads Parquet back, compares
it with `fixtures/expected.json`, prints a JSON verification summary, then cleans
up. The golden reference records logical schema and rows, rather than unstable
Parquet bytes. `fixtures/pipeline.json` is the portable input definition.

Limits: eager in-memory string tables, sequential execution, no retries,
cancellation, preview, production resource authorization or metadata persistence.
SDK validation copies tables, so this is not evidence of scalable execution.
Production CSV typing, transforms, sinks and executor hardening remain separate
issues. Polars and PyArrow are experiment-only dependencies; the API lock is unchanged.

AI assistance: Codex authored this implementation and tests. Independent student
review, hosted CI, merge and stakeholder demonstration remain pending.

Run the explicit spike test command above alongside the standard backend checks.
The GitHub token available during PR creation cannot update workflow files, so
a dedicated hosted spike check remains follow-up work. Regenerate the lock with:

```sh
uv pip compile --universal --generate-hashes --python-version 3.12 experiments/headless_etl/requirements.txt -o experiments/headless_etl/requirements.lock
```
