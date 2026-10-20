# ADR-0005: Local project identity and browser selection

Status: Proposed for independent review under issue #19.

## Decision

Use the existing SQLite Project model through versioned create/list/detail API
operations. Generated UUIDs identify projects; names are normalized display text
and never determine a filesystem path. Duplicate names are allowed and resolve
through distinct IDs. Names contain 1–128 Unicode characters after trimming;
control characters and unknown request fields are rejected. API timestamps are
explicit UTC. List results are bounded to at most 100 rows per request, with
newest-first order and ID as a stable tie-breaker.

The Projects view uses TanStack Query for server metadata and Axios for transport.
The API exposes only ID, name and creation time; relationships and workspace
bindings are not serialized. Metadata is saved before a create response returns.
No schema change or database migration is necessary.

Opening a project uses `/#/projects/:projectId/builder` and a confirming API GET.
Store only the successful project's ID in browser localStorage, scoped by the
API base URL and browser origin. `/builder` restores that identity and checks
it again. Missing projects clear the saved identity and show recovery navigation.
Network failures retain identity for Retry. Storage failures leave direct-link
navigation available but cannot promise persistence across browser sessions.

The project-scoped builder is a workspace shell, not a pipeline save/reload API.
Draft name and selected node remain ephemeral Zustand state and clear when the
project changes. Refresh loses drafts; navigating away and back in the same
project preserves them. Project metadata persists independently of browser state.

## Alternatives and consequences

Using project names as folder identifiers creates path and collision concerns.
Storing metadata in browser storage duplicates SQLite and can become stale.
A server-wide last-project setting would make local browser contexts interfere;
browser identity persistence is sufficient for this single-user local feature.
An explicit server open mutation is unnecessary because opening is a read.

The API has no rename/delete/multi-user permission operations in this story.
Offset pagination is sufficient for metadata lists but concurrent inserts may
shift page boundaries; cursor pagination can be introduced if that becomes a
measured need. Pipeline persistence belongs to #14. Clearing browser storage
does not delete server projects.

## Verification and attribution

See [usage and contracts](../../projects.md) and
[executed verification](../../testing/issue-19-local-projects.md). Planned
reviewer: `menaboulus`. Independent approval, merge and stakeholder acceptance
are pending.

AI Assistance: Karim requested #19 implementation; Codex drafted the code,
tests, design and documentation and ran the recorded automated checks. No
separate manual implementation or verification by Karim is claimed.
