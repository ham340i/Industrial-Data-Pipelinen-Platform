# Missing knowledge and independent learning

## What knowledge the team was missing

Earlier courses covered layered web applications with a REST API over a relational database. This project needed several things they did not:

| Area | What was missing | Where it was needed |
|---|---|---|
| Columnar data processing | Polars expressions, Arrow types, Parquet row groups and metadata, exact integer and float semantics | Blocks, executor, preview |
| Designing a plug-in contract | A versioned block SDK with typed ports and schema compatibility | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8) |
| Graph algorithms in a product | Topological ordering, cycle detection, strongly connected components for precise error reporting | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21) |
| Bounded parsing of untrusted files | Reading a prefix of CSV, JSON and Parquet under byte and time budgets | [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26) |
| Safe embedded SQL | SQLite authorizer, read-only connections, progress handlers | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) |
| Durable run state | Recording and recovering interrupted runs; redaction of log text | [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27) |
| In-process scheduling | Timer threads, shutdown races, deterministic timing tests | [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29) |
| Graph editing in the browser | React Flow, separating unsaved editor state from server state | [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17) |
| Accessibility of dynamic interfaces | Live regions and focus management for asynchronous validation | [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) |
| Cross-platform filesystems | Case sensitivity, reserved device names, atomic publication | [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) |

## How the knowledge was acquired

- **Spikes with a measurable result.** The headless ETL proof ([#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10)), the safe SQL spike ([#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12)) and the Polars and Arrow measurements ([#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13)) each produced a runnable experiment and a written result before the feature was built.
- **Primary documentation.** Polars, Apache Arrow and Parquet format documentation, the SQLite C interface reference, FastAPI and Pydantic documentation, React and WCAG references. Sources are cited in the individual records.
- **Review as teaching.** Several reviews found defects the author had not anticipated, and the corrections are recorded in the pull requests, for example [#52](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52), [#72](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/72) and [#74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74).

## Individual Life-Long Learning records

Each student must have their own `[LLL]` issue on the Release 1 milestone. At Release 1 these exist:

| Student | Issue |
|---|---|
| Al-Yousef | [#80](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/80): accessible React focus and error announcements |
| menaboulus | [#87](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/87): workspace containment and cross-feature contracts |

The other team members have not yet opened theirs. An issue without the `[LLL]` prefix in its title is not assessed.
