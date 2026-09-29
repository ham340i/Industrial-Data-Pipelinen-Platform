# Performance plan

No benchmarks have been run. Targets require representative stakeholder workloads and approved hardware; do not treat suggested metrics as achieved results.

| Metric | Measurement method | Target | Measured result |
|---|---|---|---|
| Pipeline execution time | Wall time for a versioned graph and synthetic dataset | TODO | Not measured |
| Data volume | Rows, bytes, columns and source format | TODO supported envelope | Not measured |
| Memory consumption | Peak resident memory for engine and preview | TODO workstation budget | Not measured |
| Preview latency | Request-to-visible result, including sampling | TODO | Not measured |
| Transformation throughput | Rows/second for identified block and input | TODO | Not measured |
| API latency, if added | Median and p95 at stated concurrency | TODO | Not applicable yet |

Record revision, dataset generator/seed, OS, CPU, RAM, runtime versions, graph, cold/warm conditions, repetitions and failures. Compare equivalent workloads; report variation and correctness alongside speed. Investigate bounded previews, streaming/batching and cancellation through measured spikes before selecting optimizations. Keep large/generated datasets outside Git and link sanitized measurement reports to issues and releases.
