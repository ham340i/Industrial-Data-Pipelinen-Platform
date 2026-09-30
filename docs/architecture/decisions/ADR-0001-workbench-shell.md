# ADR-0001: Workbench shell and state boundaries

Status: Proposed for teammate review; implemented under [issue #5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5).

## Context and decision

The first frontend must provide accessible navigation and a typed transport without coupling the future headless engine to React. Use React 19, TypeScript, Vite and MUI as specified by the release target. Use npm with a committed lockfile and Node 24 for CI. Hash routing lets static hosting and local preview support direct links without server rewrite rules.

TanStack Query exclusively owns remote health data, request cancellation and cache lifetime. Zustand owns an in-memory draft name and selection only; neither API responses nor credentials belong in this store. A draft is explicitly unsaved and is lost on refresh. Do not introduce persistence until the project and pipeline contracts exist.

Axios uses a configurable base URL, a bounded timeout and normalized errors that never display raw server payloads. Validate health responses at runtime because TypeScript alone cannot validate JSON. The provisional GET /health contract is documented in the frontend guide and still needs backend-owner agreement.

## Alternatives and consequences

A single global store for remote and draft state duplicates cache/error behavior and risks stale responses overwriting edits. Browser-history routing requires hosting rewrites; hash routing is sufficient for this shell. A complete graph editor would prematurely implement later issues, so reserve its route and make the unavailable capability explicit.

## Verification and review

Test network boundaries with synthetic HTTP mocks, including loading, malformed responses, server errors and retry. Test keyboard navigation and draft state independently. Production build, strict types, lint and formatting are required. Review by @menaboulus (substituted at the owner’s request) and backend contract agreement remain pending; this document does not assert approval.
