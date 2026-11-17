# Spike #109: eager per-block execution versus a fused Polars lazy plan

Issue: [#109](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/109) (Life-Long Learning, Release 1). Owner: ham340i.
This is an isolated sandbox. Nothing here is imported by the product, and this branch is not meant to be merged.

## Question

The executor runs each block eagerly and keeps every intermediate in memory ([design note](../../docs/architecture/local-executor.md)). Can one fused Polars lazy plan run the same pipeline on a large input within a workstation's memory, and what would it cost the per-block contract?

## Pipeline and modes

Synthetic inputs, generated deterministically: `fact.csv` with 10 columns (integer, number, boolean and five strings; every 11th `value` is null) and a 1,000-row `dimension.csv`. Pipeline: CSV source → Filter `value > 2000` → inner Join on `key` with the dimension → Aggregate per `segment` (sum and count of `value`) → Sort → Parquet sink.

| Mode | What runs |
|---|---|
| `product` | The real Release 1 `Executor` and catalog blocks, exactly as the API runs them |
| `eager` | The same steps as eager Polars calls, keeping every intermediate referenced (what the executor retains) |
| `lazy` | One fused `LazyFrame`, written with `sink_parquet` |

## Method

`python -m experiments.lazy_execution.spike measure --repeats 3`

Every run is a fresh `docker run` of the repository's digest-pinned Python 3.12.15 image, with **1 GiB memory and no swap**, 2 CPUs, `POLARS_MAX_THREADS=2` and no network. The hash-locked site-packages (Polars 1.44.2, PyArrow 25.0.1) and the checkout are mounted read-only. Time covers the pipeline only; peak memory is the worker's `ru_maxrss`, which includes native Polars and Arrow allocations. Medians of 3 runs, with the range. Raw data: [results.json](results.json).

## Results

| Mode | Fact rows | Seconds, median [range] | Peak memory MiB, median [range] |
|---|---:|---|---|
| product | 150,000 | 26.505 [26.422–27.447] | 581.6 [553.3–585.8] |
| eager | 150,000 | 0.289 [0.261–0.317] | 109.7 [109.6–110.0] |
| lazy | 150,000 | 0.287 [0.205–0.298] | 87.6 [84.5–90.3] |
| eager | 2,000,000 | 0.834 [0.71–0.875] | 672.1 [671.4–672.2] |
| lazy | 2,000,000 | 0.39 [0.362–0.396] | 265.1 [263.6–265.5] |

Output checks (automatic):
- Eager and lazy produce **identical values, order and Arrow schema** at both 150,000 and 2,000,000 rows.
- Product and lazy produce identical values at 150,000 rows. Their types differ: the product writes SDK types (`string not null`, `int64`, `int64 not null`), while Polars writes `large_string`, `int64` and `uint32` for the count.

Product above its budget: at 200,000 rows the real executor stops with `data_limit` at the Aggregate node (downstream nodes `dependency_failed`, nothing published). Its retained-data budget (10,000,000 cells) counts every block's inputs and outputs, and the CSV source alone is capped at 2,000,000 cells.

Optimized lazy plan (`LazyFrame.explain()`):

```text
SORT BY [col("segment")]
  AGGREGATE[maintain_order: false]
    [col("value").sum().alias("total"), col("value").count().alias("rows")] BY [col("segment")]
    FROM
    simple π 2/2 ["segment", "value"]
      INNER JOIN:
      LEFT PLAN ON: [col("key")]
        simple π 2/2 ["value", "key"]
          Csv SCAN [/data/fact.csv]
          PROJECT 2/10 COLUMNS
          SELECTION: col("value") > 2000
      RIGHT PLAN ON: [col("key")]
        Csv SCAN [/data/dimension.csv]
        PROJECT */2 COLUMNS
      END INNER JOIN
```

## What I learned

1. **The optimizer does the work our blocks cannot.** Polars pushed the projection into the scan (it reads **2 of 10** columns) and the filter into the scan, before the join. Our per-block design parses every column into memory first, because each block only sees its own input.
2. **At 2 million rows lazy used 61% less memory and ran about 2× faster than eager**, with identical output. Both stayed under 1 GiB on this narrow aggregate, so the definition-of-done threshold is met by lazy with wide headroom; eager is already at two-thirds of it.
3. **The real bottleneck is not eager versus lazy.** At 150,000 rows the product took 26.5 s and 582 MiB, where eager Polars took 0.29 s and 110 MiB: roughly **90× slower and 5× the memory**. The SDK v1 boundary converts every table to Python row dictionaries between blocks, and that conversion dominates. The product cannot run this pipeline at 200,000 rows at all.
4. **Fusion breaks per-block evidence.** In one fused plan there is no point between Filter and Join where the executor can count rows, validate the Join's input schema or emit a per-block event. Schema checks can still run before execution with `LazyFrame.collect_schema()`, but row counts per block would be lost.
5. **Types need normalizing at the boundary.** Polars counts are `UInt32` and strings are `large_string`; the SDK declares `integer` (Int64) and `string`. A lazy path must cast to the declared types at the sink, or the published artifact's schema changes.

## Decision for Release 2

Do **not** fuse whole pipelines into one lazy plan yet. Fix the bigger cost first, then adopt laziness where it keeps the per-block contract:

1. **Keep tables as Polars frames between blocks.** Add a frame-native block interface (SDK v2) so blocks receive and return frames, without the Python row conversion. That addresses the 90× time and 5× memory gap and lifts the practical size limit, without changing what users see.
2. **Make sources lazy.** Have file sources return `scan_csv`/`scan_parquet` lazy frames and push the downstream Select and Filter columns and predicates into the scan, collecting at the first block that needs a materialized table. This keeps per-block validation and events.
3. **Cast to declared SDK types at sinks**, so lazy and eager paths publish the same artifact schema.
4. **Re-measure** with this script after (1), and on partner hardware with an approved dataset before changing the default budgets.

## Limits of this spike

Synthetic data; one pipeline shape that aggregates to 8 rows; three runs per case; filesystem cache not flushed; one machine. It does not measure joins that expand rows, wide outputs, or concurrency, and it says nothing about partner workloads.

## AI assistance

I wrote the plan and decided the scope, modes and decision. Claude Code helped write the measurement script and draft this report; I checked the numbers against the raw results.
