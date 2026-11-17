# Security

## Context and threat model

The product is a single-user tool that runs on one workstation. Assets are the partner's manufacturing data, database files, pipeline definitions, run logs and published outputs. The realistic threats are:

1. A pipeline definition or request that reads or writes files outside the project's workspace.
2. A query that modifies a source database or exhausts the machine.
3. Credentials or machine paths leaking into shared definitions, logs or error messages.
4. A malformed or oversized file that crashes or stalls the process.
5. Another machine on the network reaching the API.

## Controls implemented

| Threat | Control | Code | Tests |
|---|---|---|---|
| File access outside the workspace | Every resource reference is validated as a relative path without traversal or reserved names, resolved, and required to stay inside the project's folder with the expected extension | [resources.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/resources.py) | [test_file_blocks.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_file_blocks.py), [test_file_policy.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_file_policy.py) |
| Choosing an arbitrary workspace folder | The user can only select folders the administrator listed in `LPS_ALLOWED_WORKSPACE_ROOTS` | [workspace.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/workspace.py) | [test_workspace_settings.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_workspace_settings.py) |
| SQL injection or writes | Database opened read-only, `query_only` pragma, an authorizer that permits read actions only, a single validated `SELECT`, bound parameters, no string interpolation of values | [sources/sql.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/sources/sql.py), [blocks/sql.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/sql.py) | [test_sql_source_contract.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_sql_source_contract.py), [test_sql_block.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_sql_block.py) |
| Unsafe evaluation | Filters and transforms are built from a fixed set of operators on validated configuration; there is no `eval`, `exec` or shell call anywhere in the application | [transforms.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/transforms.py) | [test_transform_blocks.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_transform_blocks.py) |
| Credentials in shared definitions | Pipeline and block configuration reject credential-named keys and machine paths | [contracts.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/contracts.py) | [test_pipelines.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_pipelines.py) |
| Secrets in logs | Run log text is redacted for URL credentials, key and value secrets and machine paths before it is stored; request logs record method, path, status and timing only | [redaction.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/redaction.py), [main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py) | [test_run_redaction.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_run_redaction.py), [test_logging_config.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_logging_config.py) |
| Internal details in errors | All errors use one envelope with a stable code and fixed message; unhandled exceptions return a generic message while the stack trace stays in the server log | [main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py) | [test_contract.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_contract.py) |
| Oversized or hostile input | Byte, row, column, cell, record and time budgets on every read, preview and query; request bodies are capped before JSON parsing | [preview_policy.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/preview_policy.py), [preview/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/api.py) | [test_file_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_file_preview.py), [test_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_preview.py) |
| Network exposure | Compose publishes both services on `127.0.0.1` only; browser origins are limited to the workbench by CORS | [compose.yml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/compose.yml), [config.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/config.py) | [scripts/tests/test_workspace.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/scripts/tests/test_workspace.py) |
| Container privileges | The API image runs as a non-root user with `no-new-privileges` | [api.Dockerfile](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docker/api.Dockerfile) | Same |
| Supply chain | Hash-pinned Python lock, npm lockfile, `npm ci --ignore-scripts`, Actions pinned to commit SHAs, CI token limited to read access, weekly Dependabot | [requirements.lock](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/requirements.lock), [ci.yml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/workflows/ci.yml) | CI |
| Secrets in the repository | `.gitignore` excludes `.env`, key and credential files and data folders; a CI check scans for common secret patterns; fixtures are synthetic | [.gitignore](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.gitignore), [check_repository.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/scripts/check_repository.py) | CI |

## Authentication and authorization

There are no user accounts, passwords or roles, by design. The application has exactly one user, the person logged in to the workstation, and it listens only on the loopback interface. Access control is therefore the operating system's: whoever can use that account can use the tool and read its files. The authorization that does exist is enforced on the server before any file is touched: a request can only reach files inside its own project's folder, and only inside a workspace the administrator allowed.

Consequences we accept for Release 1: any local process running as the same user can call the API. If the tool is ever shared between users or exposed beyond loopback, authentication becomes mandatory and must be added before that deployment.

Because there are no passwords, password hashing does not apply.

## Project-specific security requirements

| Requirement | Source | Status |
|---|---|---|
| No credentials or machine paths in portable definitions | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) | Implemented |
| Read-only, parameterized SQL | [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23) | Implemented |
| File access contained to the project workspace | [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) | Implemented |
| Redacted run logs | [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27) | Implemented |
| Bounded preview that cannot trigger sinks or timers | [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26) | Implemented |
| Hardening review of file, SQL and configuration boundaries | [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | **Open**: pull request [#88](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/88) not yet reviewed |

## Reporting a problem

See [SECURITY.md](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/SECURITY.md). Do not post secrets or partner data in an issue.
