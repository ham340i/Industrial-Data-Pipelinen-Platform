# Release 1 candidate: install, operate and recover

This guide is for a stakeholder tester or teammate who wants to install the Release 1 candidate, demonstrate it with synthetic data, and recover from mistakes, all without editing source code. Issue [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) tracks this packaging work.

Everything goes through one command, `scripts/release_candidate.py`. It wraps the repository's `compose.yml` under a single Compose project name (`lps-release` by default), so it never touches another stack, container or volume on your machine.

## Requirements

- Docker Engine or Docker Desktop with Compose v2 (`docker compose version`).
- Python 3.12 or newer on the host. The command uses the standard library only; no `pip install` is needed.
- A clone of this repository at the revision you want to test.

No accounts, credentials or network services are required. Both services listen on `127.0.0.1` only.

## Configure

Copy the example settings and change the ports only if 3000 or 8000 are taken:

```bash
cp .env.example .env
python3 scripts/release_candidate.py config
```

`config` prints the settings the candidate will use, or explains what is wrong. Only these keys are accepted:

| Setting | Meaning | Default |
|---|---|---|
| `FRONTEND_PORT` | Loopback port for the web application | `3000` |
| `API_PORT` | Loopback port for the API | `8000` |
| `LPS_LOG_LEVEL` | API log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |

Any other key is refused, so secrets and data paths cannot end up in `.env`. The two ports must differ.

## Build, start, stop

```bash
python3 scripts/release_candidate.py build    # build both images
python3 scripts/release_candidate.py start    # build if needed, start, wait for health checks
python3 scripts/release_candidate.py status   # show the candidate's containers
python3 scripts/release_candidate.py stop     # stop containers, keep all data
```

`start` returns only after the API and the frontend's API proxy both answer their health checks. It prints the address to open, normally <http://127.0.0.1:3000>.

## Load the demonstration data

```bash
python3 scripts/release_candidate.py demo
```

`demo` needs a running candidate. It creates a project named `Release 1 demo <timestamp>` with two synthetic inputs: six sensor readings as CSV and three asset labels in SQLite. It then saves and runs the Release 1 target graph twice:

```text
CSV -> Validate Schema -> Filter (reading > 10) --+
                                                  +-> Join -> Aggregate (sum per label) -> Parquet
SQL Source (labelled assets) ---------------------+
```

The command checks every block's row counts and the published Parquet rows, `A = 30` and `B = 50`, and prints the project address. Open it to show the graph, its runs, the block timings and the output rows. You can run `demo` again at any time; each run creates a new project.

## Recording the demonstration

1. Run `reset --yes`, then `start`, then `demo`, so the recording starts from a known state.
2. Record the browser only, at a fixed window size. Do not record terminals that show tokens or personal folders.
3. Show the steps in the Release 1 order: open the project, the graph, validation, a selected-node preview, the run history, a run's block timings and logs, and the Parquet output rows. Then rerun the pipeline from the UI.
4. Note the repository revision (`git rev-parse HEAD`) and the date in the video description, and link it from the [tag checklist](tag-checklist.md).

## Back up, restore and reset

Candidate data lives in one Docker volume: the SQLite metadata database and every project's data folder.

```bash
python3 scripts/release_candidate.py backup                 # writes ./backups/lps-backup-<UTC>.tar.gz and .json
python3 scripts/release_candidate.py restore backups/lps-backup-<UTC>.json --yes
python3 scripts/release_candidate.py reset --yes            # delete all candidate data
```

- **Backup** stops the containers for a moment so the database is copied in a consistent state. It restarts them if they were running. The `.json` manifest records the archive's SHA-256 checksum, the database schema revision and the Git revision that wrote it. `backups/` is ignored by Git; keep backups out of the repository.
- **Restore** first builds the images of the revision you have checked out. It then checks the backup's checksum and schema revision against that build, before it stops anything. It refuses a damaged archive, and it refuses a backup whose schema this revision does not know. Only then does it replace all candidate data with the archive. If the candidate was running, restore restarts it on freshly created containers from that build.
- **Reset** removes this candidate's containers and its data volume only. Images and other Compose projects are untouched.

`restore` and `reset` delete data, so both require `--yes`.

## Rollback and data compatibility

- **Upgrading is automatic.** The API upgrades the database to the newest schema when it starts. A backup from an older candidate can therefore be restored into a newer one.
- **Downgrading is not automatic.** Once a newer candidate has started on your data, an older candidate cannot open it. To roll back, check out the older revision, then restore a backup made by that older revision (or any earlier one). `restore` names the revision you need when the schema is too new. Because restore rebuilds and recreates the containers, a newer candidate that was still running cannot reopen the restored data and migrate it forward again.
- **Back up before every upgrade.** That backup is your rollback point.
- Saved pipelines are versioned JSON with `schema_version: 1`. Release 1 reads only that version.
- Output files written by a run are plain files under the project folder. They are kept by backups and removed by reset.

## Rehearsal used by CI

```bash
python3 scripts/release_candidate.py smoke --report
```

`--report` also writes the JSON result to `test-results/release-candidate.json`, the fixed location CI uploads.

`smoke` rehearses the whole lifecycle in a throwaway project named `lps-rc-smoke-<random>`, on random loopback ports:

1. Clean install from an empty volume, with both health checks.
2. The demonstration scenario: two runs, every block count and the output rows.
3. Recreate the containers; the project, pipeline, runs and output must survive.
4. Back up while running, reset, confirm the candidate starts empty, restore, and confirm everything is back.
5. Rollback: mark the database with a schema this candidate does not know, as a newer release's data would be, and back it up. Restore must refuse that backup and leave the data untouched. Then restore the older backup and confirm everything reopens.

It always removes its containers and volume, even when a step fails, and fails if anything is left behind. The "Release candidate rehearsal" CI job runs it on every pull request and uploads the JSON report.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `Port ... must be a number` or `must differ` | Fix `.env`; `config` shows the values in use. |
| `Unsupported setting(s)` | Remove the key from `.env`. The candidate has no other settings. |
| `Start the candidate first` | Run `start`, then `demo`. |
| A port is already in use | Change `FRONTEND_PORT` or `API_PORT` in `.env`, then `start`. |
| `Backup schema ... is newer` | Check out the revision named in the message, or use a newer candidate. |
| You want a clean slate | `reset --yes`, then `start`. |

Known limitations are listed in the [release notes](release-notes.md).
