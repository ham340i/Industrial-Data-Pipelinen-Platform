# Security plan

Status: proposed application controls; repository ignore rules and limited checks implemented. No product controls have been tested.

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

## Current implementation and remaining product controls

No product authentication/authorization, API, network server or database exists. Rate limiting and application error handling are therefore not implemented; add them when an actual exposed interface requires them. Repository helpers use existing credentials without printing values, and CI uses read-only permissions. The private-reporting entry point is [SECURITY.md](../../SECURITY.md); a dedicated private contact still needs team confirmation.

Live main-branch protection now requires independent review, both GitHub Actions checks and conversation resolution. Existing third-party integrations still need owner review; a neutral SonarCloud check is not evidence of a passed security audit.
