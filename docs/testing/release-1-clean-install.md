# Release 1 clean install on a second machine

Revision: `5d05187c82ed62e30d2283c8a57e56990abd8ad1` (`main` after #106). Date: November 17, 2026. Performed by ham340i, with AI assistance (Claude Code) running the commands; the outputs below are copied from the run.

## Machine

| Item | Value |
|---|---|
| Operating system | Ubuntu 24.04.5 LTS, Linux 6.18.44, x86_64 (a cloud Linux container, not a team member's development machine) |
| Docker | Docker Engine 29.9.2, Docker Compose v5.6.1 |
| Python | 3.13.18 |
| Starting state | Fresh `git clone` of the repository, checked out at `5d05187`; no images, containers or volumes from this project |

## Deviation from the guide

This machine reaches the internet only through an HTTPS proxy that presents its own certificate, which the image builds do not trust. The local clone therefore had one change, never committed: both Dockerfiles copy that certificate and set `PIP_CERT` (API) or `NODE_EXTRA_CA_CERTS` and `NPM_CONFIG_CAFILE` (frontend), with `.dockerignore` allowing the file. Nothing else differed from [candidate.md](../release-1/candidate.md). A machine with direct internet access needs no change.

## Steps and results

| Step (from candidate.md) | Result |
|---|---|
| `cp .env.example .env`, `python3 scripts/release_candidate.py config` | Printed project `lps-release`, ports 3000 and 8000, log level `INFO` |
| `start` | Built both images and started; both health checks passed in 1 min 21 s; printed `http://127.0.0.1:3000`. `status` showed both containers healthy, bound to `127.0.0.1` only |
| `demo` | Created project "Release 1 demo 2026-11-17 21:01", saved the pipeline and ran it twice; output rows `A = 30`, `B = 50`, checked by the command |
| `backup` | Wrote `lps-backup-20261117T210211Z.json` and `.tar.gz` (12,214 bytes); manifest records revision `5d05187`, schema `0004` and the SHA-256 checksum |
| `reset --yes` | Removed the containers and the data volume; `status` listed nothing |
| `restore <manifest> --yes` | Rebuilt the images, verified the checksum and schema, restored the data |
| `start` after restore | The demo project, its 2 succeeded runs and the output rows `A = 30`, `B = 50` were all back (checked through the API) |
| `smoke --report` (the CI rehearsal) | `outcome: passed` for revision `5d05187`: clean install, acceptance, persistence, backup, reset, restore and rollback. Report: [release-1-clean-install-rehearsal.json](release-1-clean-install-rehearsal.json) |

The same revision also passed every job in CI, including "Release candidate rehearsal": [CI run](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/44171669873).

## Demonstration recording

Made afterwards on the same machine, as [candidate.md](../release-1/candidate.md#recording-the-demonstration) describes: `reset --yes`, `start`, `demo`, then the browser only at 1440 by 900, driven by Playwright. Steps in order: open the project, the graph, validation ("Ready to run. No problems found."), a selected-node preview of the CSV source (6 sampled rows), the run history, a run's block timings and logs, the Parquet output rows (`A 30`, `B 50`), then a rerun from the UI with the same rows. All 8 steps passed. Video (28 seconds, no narration): [release-1-candidate-demo.webm](../demos/release-1-candidate-demo.webm).
