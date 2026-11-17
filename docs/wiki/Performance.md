# Performance

## Requirements

The tool runs on an ordinary engineering workstation next to other work. The requirements are:

1. The interface stays responsive: a preview returns in a few seconds or fails with a clear message.
2. A mistaken pipeline or a huge file cannot exhaust memory or stall the machine.
3. Run status is available while a run is in progress.

No throughput target has been agreed with the partner, because no representative workload has been supplied. The team measured synthetic representative workflows instead ([#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35), below).

## Bottlenecks and how each is addressed

| Bottleneck | Approach | Code |
|---|---|---|
| Previewing a large file would read all of it | Preview reads a prefix through an unbuffered, byte-counted reader: at most 2 MiB per source, 64 KiB per record, 128 columns, and stops after the requested rows | [preview_policy.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/preview_policy.py), [csv_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/csv_preview.py), [json_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/json_preview.py) |
| Parquet decoding can expand far beyond file size | Footer capped at 256 KiB; the declared and dictionary-expanded decoded size is checked against a budget before any data is expanded, in both execution and preview; only the leading row groups needed for a preview sample are read | [parquet_decode.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/parquet_decode.py), [file_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/file_preview.py) |
| A slow preview blocks the next one | Each preview has a 5 second budget and is cancelled when the browser disconnects; at most two previews run at once; requests over 256 KiB and responses over 2 MiB are refused | [preview/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/api.py), [preview/models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/models.py) |
| Preview recomputing the whole graph | Only the selected node's single input path is evaluated, up to 20 nodes | [preview/service.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/service.py) |
| A run holding every intermediate table | The executor tracks retained rows and cells across the run and stops at 1,000,000 rows or 10,000,000 cells; graphs are limited to 1,000 nodes | [runtime.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/execution/runtime.py) |
| Row-by-row Python transforms | Transforms run as vectorized Polars expressions | [transforms.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/transforms.py), [relational.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/relational.py) |
| Querying an output would load the file | DuckDB reads only the requested columns and rows from Parquet, single thread, 64 MB memory limit, at most 500 rows and 100 columns per page | [artifacts/query.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/artifacts/query.py) |
| Lists growing without bound | Project, pipeline and run lists are paginated; run and block lookups use indexed foreign keys | [pipelines/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/api.py), [models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/metadata/models.py) |
| Runaway SQL | SQLite progress handler stops a query after a configured number of VM steps and on cancellation | [blocks/sql.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/sql.py) |
| Polling for run status | The workbench polls with TanStack Query and discards stale responses, instead of holding a streaming connection | [RunMonitor.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/RunMonitor.tsx) |

## Measurements

### Representative bounded workflows (#35)

A synthetic fact CSV with duplicate keys and periodic nulls is joined to a dimension, aggregated per segment, sorted and published as a registered Parquet output, through the real services with telemetry. Docker limited each run to 2 CPUs and 1 GiB; three fresh-process trials per row, medians shown.

| Case | Fact rows by columns | Execution | Input rows per second | Peak memory | Preview | Repeated output query |
|---|---|---|---|---|---|---|
| Small | 100 by 6 | 0.19 s | 529 | 249 MiB | 6.6 ms | 20.8 ms |
| Medium | 1,000 by 10 | 0.43 s | 2,328 | 245 MiB | 8.5 ms | 20.9 ms |
| Wide | 3,000 by 26 | 1.54 s | 1,950 | 262 MiB | 12.4 ms | 19.5 ms |
| Wide, Select before Join | 3,000 by 26 | 1.05 s | 2,847 | 255 MiB | 12.3 ms | 20.3 ms |

Finding: on the wide graph the join dominates (691 ms of the run). Projecting columns before the join cut the whole run by about 31.5%; on small and medium inputs it made no reliable difference. The team therefore recommends early projection as a pipeline-authoring practice rather than an automatic optimizer. Both budget-failure probes stopped the run without publishing any output. Full method, raw data and limits: [report](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-35-workloads.md), [raw results](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-35-results.json), [runner](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/experiments/workloads/README.md), [tests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_workload_benchmark.py).

### Polars and Arrow behaviour (#13)

The Polars and Arrow spike ([#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13)) measured conversion, Parquet write and read, preview time and peak memory in a container limited to 2 CPUs and 1 GB. Medians of three runs:

| Case | Rows by columns | Parquet write | Parquet read | Preview | Peak memory |
|---|---|---|---|---|---|
| Small | 1,000 by 10 | 1.9 ms | 66.7 ms | 0.05 ms | 152 MiB |
| Wide | 5,000 by 128 | 16.4 ms | 69.8 ms | 0.04 ms | 168 MiB |
| Null-heavy | 100,000 by 10 | 41.8 ms | 78.6 ms | 0.03 ms | 210 MiB |

Method, environment and raw results: [report](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-13-polars-arrow.md), [raw data](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-13-results.json), [reproducer](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/experiments/polars_arrow/README.md). These are synthetic fixtures, not partner workloads.

## Known limits

- Execution is sequential within one process. Independent branches of a graph are not run in parallel.
- The limits above are fixed defaults chosen for safety. The #35 measurements stay well inside them but were not run on partner hardware or data, so they are observations, not accepted capacity figures.
- Byte budgets bound what is read and declared, not the native allocator's peak memory.
