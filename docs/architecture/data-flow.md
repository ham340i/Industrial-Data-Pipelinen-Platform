# Data flow

Status: planned; no pipeline runs have occurred.

1. Select an approved source and reference its existing schema/data contract.
2. Configure a graph in the visual builder; serialize a pipeline definition without secrets.
3. Resolve local paths and credential references at runtime; validate configuration and source permissions.
4. Ingest data into the local engine. Apply transformations and schema/data-quality checks under explicit block contracts.
5. Expose bounded intermediate previews and redacted diagnostics. Decide cancellation, retry and partial-failure behavior before implementation.
6. Publish governed outputs only after required validation; record input identity, pipeline revision and run outcome.
7. Allow authorized analytics/ML consumers to use outputs under the approved data contract.

Sensitive boundaries: source access, preview rendering, logs, temporary files and publication. Retention, deletion, invalid-row handling and atomic output behavior require ADRs and tests. Synthetic fixtures must cover nulls, malformed inputs, schema drift, join cardinality and precision loss.
