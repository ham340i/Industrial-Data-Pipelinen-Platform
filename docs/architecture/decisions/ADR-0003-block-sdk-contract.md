# ADR-0003: Headless versioned Block SDK contracts

- Status: Proposed
- Date: 2026-10-06
- Related issues: [Issue #8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8)

## Context

Issue #8 requires a reusable contract for block identity, typed ports,
configuration and data schemas, validation, execution, optional preview,
runtime context, logging, structured failures and registry metadata.

The contract must be testable without a frontend. The approved implementation
scope covers the SDK, one synthetic block, fixtures, tests and documentation.
It uses Python and the existing Pydantic dependency.

Implementation was authorized separately. This ADR remains proposed pending
approval of the documentation and recording of the decision participants
through the linked issue discussion.

## Decision

Use the contracts implemented in `app/blocks/`:

- `BlockDescriptor` declares identity, ports and preview capability.
- `BlockConfig` defines strict public configuration and its JSON schema.
- `DataSchema`, `Table` and `ControlSignal` represent typed data and control values.
- `Block` validates invocation boundaries and provides execution, lifecycle
  hooks and a separate optional preview implementation.
- `BlockContext` supplies run/node identity and injected runtime callbacks.
- `BlockFailure` provides structured public errors independently of HTTP.
- `BlockRegistry` registers blocks explicitly, resolves exact ID/version pairs
  and exports validated public metadata snapshots.

SDK interface version `1` is separate from each block's version. Block versions
are opaque strings; registration and resolution use exact matches.

Public metadata contains declarations and configuration schemas. Runtime
callbacks, concrete configuration values and table rows are excluded.

The synthetic Add Constant block demonstrates the extension interface using
golden and invalid-configuration fixtures.

## Alternatives

- Independent functions for each block: simpler initially, but validation,
  metadata, preview and failure handling would vary between implementations.
- Automatic discovery or latest-version resolution: reduces explicit setup,
  but introduces implicit loading and version-selection behavior.
- Preview through normal execution: reuses execution code, but could invoke
  publishing behavior. Preview therefore has a separate extension method.

These alternatives were considered during design; no comparative prototype
or benchmark is claimed.

## Consequences

Blocks share a headless interface that can be exercised directly in Python.
Registration is explicit, and multiple versions of a block can coexist.

The table contract intentionally supports string, integer, number and boolean
columns with explicit nullability. Block authors must keep invocation state
out of shared instance fields and provide safe public descriptions and errors.

Graph scheduling, graph-wide schema propagation, persistence integration,
production blocks and API/frontend integration remain separate work.

## Risks

- Nested dictionaries remain mutable despite frozen model fields. Invocation
  boundaries detach and revalidate table values.
- Known credential keys are rejected, but arbitrary secret strings cannot be
  detected automatically. Authors must review public defaults and error text.
- Preview budgets constrain returned rows and cells. They do not provide
  timeouts, memory isolation or protection against author-created side effects.
- Registry resolution detects descriptor changes and replacement configuration
  classes. It does not detect every change to implementation code.
- Recorded local verification used Python 3.13.1. Verification on the project's
  Python 3.12 target and remote CI remains pending.

  Joseph led and delivered this metadata design and implementation, with AI assistance. Independent design review is tracked in PR #57.