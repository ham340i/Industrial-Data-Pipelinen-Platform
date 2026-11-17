# Performance

## Requirements

The tool runs on an ordinary engineering workstation next to other work. The requirements are:

1. The interface stays responsive: a preview returns in a few seconds or fails with a clear message.
2. A mistaken pipeline or a huge file cannot exhaust memory or stall the machine.
3. Run status is available while a run is in progress.

No throughput target has been agreed with the partner, because no representative workload has been supplied. Measuring one is [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35), which is open.

## Bottlenecks and how each is addressed

| Bottleneck | Approach | Code |
|---|---|---|
| Previewing a large file would read all of it | Preview reads a prefix through an unbuffered, byte-counted reader: at most 2 MiB per source, 64 KiB per record, 128 columns, and stops after the requested rows | [preview_policy.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/preview_policy.py), [csv_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/csv_preview.py), [file_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/file_preview.py) |
| Parquet decoding can expand far beyond file size | Footer capped at 256 KiB; only the leading row groups needed for the sample are decoded, within an 8 MiB declared decode budget | [parquet_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/parquet_preview.py) |
| A slow preview blocks the next one | Each preview has a 5 second budget and is cancelled when the browser disconnects; at most two previews run at once; requests over 256 KiB and responses over 2 MiB are refused | [preview/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/api.py), [preview/models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/models.py) |
| Preview recomputing the whole graph | Only the selected node's single input path is evaluated, up to 20 nodes | [preview/service.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/service.py) |
| A run holding every intermediate table | The executor tracks retained rows and cells across the run and stops at 1,000,000 rows or 10,000,000 cells; graphs are limited to 1,000 nodes | [runtime.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/execution/runtime.py) |
| Row-by-row Python transforms | Transforms run as vectorized Polars expressions | [transforms.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/transforms.py), [relational.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/relational.py) |
| Querying an output would load the file | DuckDB reads only the requested columns and rows from Parquet, single thread, 64 MB memory limit, at most 500 rows and 100 columns per page | [artifacts/query.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/artifacts/query.py) |
| Lists growing without bound | Project, pipeline and run lists are paginated; run and block lookups use indexed foreign keys | [pipelines/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/api.py), [models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/metadata/models.py) |
| Runaway SQL | SQLite progress handler stops a query after a configured number of VM steps and on cancellation | [blocks/sql.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/sql.py) |
| Polling for run status | The workbench polls with TanStack Query and discards stale responses, instead of holding a streaming connection | [RunMonitor.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/RunMonitor.tsx) |

## Measurements

The Polars and Arrow spike ([#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13)) measured conversion, Parquet write and read, preview time and peak memory in a container limited to 2 CPUs and 1 GB. Medians of three runs:

| Case | Rows by columns | Parquet write | Parquet read | Preview | Peak memory |
|---|---|---|---|---|---|
| Small | 1,000 by 10 | 1.9 ms | 66.7 ms | 0.05 ms | 152 MiB |
| Wide | 5,000 by 128 | 16.4 ms | 69.8 ms | 0.04 ms | 168 MiB |
| Null-heavy | 100,000 by 10 | 41.8 ms | 78.6 ms | 0.03 ms | 210 MiB |

Method, environment and raw results: [report](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-13-polars-arrow.md), [raw data](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/performance/issue-13-results.json), [reproducer](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/experiments/polars_arrow/README.md). These are synthetic fixtures, not partner workloads.

## Known limits

- Execution is sequential within one process. Independent branches of a graph are not run in parallel.
- The limits above are fixed defaults chosen for safety, not tuned against a real workload. Tuning follows [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35).
- Byte budgets bound what is read and declared, not the native allocator's peak memory.
