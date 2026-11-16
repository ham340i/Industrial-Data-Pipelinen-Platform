# Security plan

Status: local product controls implemented and tested for the Release 1 file, SQL, artifact and configuration boundaries ([issue #32 evidence](../testing/issue-32-security-boundaries.md)). Authentication, authorization and network connectors remain out of scope.

## Threat model to validate

Assets: manufacturing inputs, source credentials, pipeline definitions, previews, run logs and published outputs. Trust boundaries: imported files, external connectors, block execution, UI/engine communication and output consumers. Candidate threats include malicious files/paths, unsafe SQL or REST parameters, untrusted blocks, leaked previews and unintended network exposure. Assign owners and link threat-model issues before implementation.

## Planned controls

- Execute locally by default; document every intentional network connection. Bind a future local API to loopback by default and assess authentication/origin protection.
- Resolve credentials outside portable pipeline definitions. Choose an OS credential store or approved mechanism in an ADR; environment variables may pass local secrets but must never be logged or exported.
- Provide `.env.example` only when actual variables exist, with placeholders only. Ignore `.env`, credential/key/token directories and private key formats.
- Use least-privilege, preferably read-only source accounts; separate output permissions. Apply access control where artifacts or APIs are shared.
- Validate paths, file type/size, schema and inputs. Define traversal/symlink behavior, archive limits and safe query parameterization. Avoid executing imported arbitrary code.
- Validate API destinations, timeouts, response size and authentication; evaluate SSRF if user-configured endpoints are supported.
- Keep credentials isolated from graphs, block metadata, logs, previews and crash reports. Redact sensitive fields; configure retention and deletion.
- Keep local datasets, generated outputs and sensitive manufacturing files out of Git. Ignore rules cover designated local directories, not every possible filename; review new files before commit. Only approved synthetic fixtures belong in the repository.
- Once dependencies exist, commit lockfiles, enable ecosystem-specific Dependabot and evaluate vulnerabilities. Actions updates are configured now.

## Repository checks and response

`python3 scripts/check_repository.py` performs a limited filename/private-key/token-pattern check and reports **paths only**, never matching values. It is not comprehensive secret scanning. GitHub secret scanning/push protection should be enabled if available after the owner reviews settings.

If exposure is suspected: privately notify the repository owner without posting values; revoke/rotate credentials; determine scope; remove data from current files and coordinate any history cleanup with the team. Deletion alone does not revoke a secret. Do not rewrite shared history without coordination. No secrets were found in the inspected initial commit; remote-only content was not audited.

## Implemented local controls (#32)

- **Workspace confinement.** Every file source, sink, preview and artifact
  query resolves its relative `resource_ref` with `resource_path`
  (`app/blocks/files.py`) beneath the project folder chosen by
  `project_data_folder` (`app/workspace.py`). Links are followed before the
  containment check, so traversal, absolute, drive, UNC, device names and
  symlinks or junctions leading outside the project are refused with
  `unsafe_resource`. Sinks write through a temporary file in the confined
  target folder and publish atomically.
- **Read-only SQL.** Only single `SELECT`/`WITH` statements pass the lexical
  policy; SQLite opens with `mode=ro` and `query_only`, and an authorizer
  denies every action other than reads (including `PRAGMA`, `ATTACH`,
  `pragma_*` table-valued functions and extension loading). Value length,
  VM steps, rows and result bytes are budgeted in both the workspace block
  and the standalone `read_sqlite_source`.
- **Artifact queries.** Arbitrary SQL is not accepted. DuckDB runs a fixed
  projection template on a connection locked to the one resolved Parquet
  file, with extensions and external access disabled.
- **Bounded inputs.** Byte, row, column and cell limits apply to every
  source; Parquet is additionally bounded by declared page bytes and by its
  dictionary-expanded size before decoding.
- **Credential-free definitions.** `app/secret_policy.py` is the one
  key-name policy for block configuration, saved definitions and the SQL
  source; definitions also refuse absolute or home-relative paths and URLs
  with embedded credentials. Environment variables carry only public
  settings; `.env.example` files are tested to stay that way.
- **Redaction.** Run messages pass through `app/runs/redaction.py`
  (credential key/value pairs including compound names, URL userinfo,
  Authorization headers, machine paths). Logs record exception types, not
  exception text. API errors use fixed messages.
- **Dependencies.** Lockfiles are hashed (Python) or integrity-pinned (npm);
  Dependabot watches GitHub Actions, pip and npm.

## Accepted risks and threat-model decisions

Recorded for #32. The trust boundary is the API process user: anyone who can
already write inside the workspace with that user's permissions is trusted.

| Decision | Rationale |
|---|---|
| Hard links inside the workspace are not detected | A hard link is indistinguishable from a regular file by path. Creating one requires local write access to the workspace and the same filesystem, which already grants the API user's access. |
| Resolve-then-open races (TOCTOU) by a local user are out of scope | Swapping a path component between the containment check and the open also requires local write access to the workspace. No remote input can do it. |
| Parquet size checks trust writer-declared metadata for plain pages | Dictionary expansion is computed from actual values; plain-encoded page sizes come from the footer. Row/cell limits and the DuckDB memory limit remain as backstops. Corrupt-codec behaviour is not a process-isolation boundary. |
| Secret detection is key-name based | Values stored under public names, or secrets in query text, are not detected. Users must not put credentials in configuration; SQLite needs none. |
| The loopback API has no authentication | Compose publishes on `127.0.0.1` only and CORS is limited to the local frontend. Shared or networked deployment requires authentication first. |
| pytest 8.4.2 advisory and lint-chain moderates stay open | Test/lint-only exposure; the fixes require a major pytest upgrade or a typescript-eslint downgrade. See the [dependency review](../testing/issue-32-security-boundaries.md#dependency-review). |

## Repository response and remaining controls

The private-reporting entry point is [SECURITY.md](../../SECURITY.md); a dedicated private contact still needs team confirmation. Repository helpers use existing credentials without printing values, and CI uses read-only permissions. Rate limiting is not implemented because the API is loopback-only.

Live main-branch protection now requires independent review, both GitHub Actions checks and conversation resolution. Existing third-party integrations still need owner review; a neutral SonarCloud check is not evidence of a passed security audit.
