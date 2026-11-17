# karimikhaeil — Iteration 4 issue #35

Karim requested the assigned representative workload benchmark on November 16,
2026. Codex fetched main, verified prerequisites #24/#26/#28 were closed and
implemented the isolated benchmark on `feature/35-workload-benchmarks`.

- [Experiment and reproduction](../../experiments/workloads/README.md).
- [Measurements, decisions and limitations](../performance/issue-35-workloads.md).
- [Correctness and integration tests](../../tests/test_workload_benchmark.py).

The experiment compares wide and projected graphs, verifies independent output
oracles and records real executor/preview/query latency, process peak RSS,
throughput, variation and failure probes. It adds no production dependencies,
default changes or timing thresholds. Planned reviewer: `menaboulus`.

AI Assistance: Karim supplied direction and authorized implementation. Codex
designed, implemented and ran the recorded experiment, tests and documentation.
No separate manual implementation/verification by Karim, independent teammate
approval, stakeholder hardware validation or stakeholder signoff is claimed.
