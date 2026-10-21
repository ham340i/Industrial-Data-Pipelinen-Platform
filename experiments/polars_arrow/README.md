# Issue #13: Polars / Arrow experiment

An isolated synthetic spike, not a production block or change to the API's
dependency lock. Exact experiment versions are Polars 1.44.2 and PyArrow 25.0.1.
The standalone lock is generated with uv 0.13.0 and verified during installation.

From the repository root with Docker running:

```powershell
docker build -t lps-polars-arrow-spike experiments/polars_arrow
docker run --rm --network none --cpus=2 --memory=1g lps-polars-arrow-spike python -m unittest -v
docker run --rm --network none --cpus=2 --memory=1g lps-polars-arrow-spike
```

The default command emits JSON with nine independent worker results, min/median/
max metrics, environment and source/lock fingerprints. To save it privately:

```powershell
docker run --rm --network none --cpus=2 --memory=1g lps-polars-arrow-spike | Set-Content -Encoding utf8 local-spike-results.json
```

Each worker generates its own fixture and deletes its temporary Parquet file.
It checks exact schema/value/order preservation through Polars to Arrow and
Parquet, plus a deliberate lossy float conversion. A failed assertion or worker
timeout makes the command fail. The Linux-only RSS method is intentional; host
Windows Python is not used for comparable memory measurements. Docker Desktop
overhead and the host's other work can affect timing.

The six unittest methods additionally cover empty/single-row/wide fixtures,
reference values, determinism, preview bounds, corruption detection, stdout
report generation and rejection of absolute/relative output-path arguments.

Reports are emitted only on stdout. The script does not accept `--output` or
write to caller-supplied filenames; the invoking shell owns any explicit output
redirection. The regression test confirms rejected output arguments cannot
overwrite an existing file, including a relative traversal target.

Fixture sizes are fixed in `CASES`, not user-supplied unbounded workloads. Repeat
counts are restricted to 1–10. Temporary storage is inside the disposable
container. No partner data, secrets, API or database service is accessed.

Lint/format these standalone files with Ruff's `--isolated` mode because root
`pyproject.toml` includes application sources only. For example:

```powershell
python -m ruff check --isolated --target-version py312 --select E,F,W,B,UP experiments/polars_arrow/spike.py experiments/polars_arrow/test_spike.py
python -m ruff format --check --isolated experiments/polars_arrow/spike.py experiments/polars_arrow/test_spike.py
```

Regenerate the experiment lock after an intentional dependency change:

```powershell
uv pip compile --universal --generate-hashes --python-version 3.12 experiments/polars_arrow/requirements.txt -o experiments/polars_arrow/requirements.lock
```

See [observed results and limitations](../../docs/performance/issue-13-polars-arrow.md).
Tests are explicitly run by the commands above; they are not yet part of hosted
application CI. AI Assistance: Codex implemented and ran this experiment at
Karim's instruction; independent review remains pending.
