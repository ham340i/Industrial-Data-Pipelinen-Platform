# Run results and downloadable logs

The Builder monitors persisted runs for its selected project and saved pipeline. The panel shows the selected run's result, saved revision, duration, output row count, available outputs, and failed blocks. Successful/skipped blocks and individual log events are kept in the downloaded log. Configuration links are available only for existing failed nodes on the matching saved revision.

The newest run is selected initially. Explicit selection stays pinned while new runs arrive. Previous runs and Older runs page through history in groups of 20. List queries include project, pipeline and page identity; detail responses are validated against the requested identity. Old requests consume AbortSignals and inactive details are collected. Active results poll until completion. Refresh and reconnect recover read errors without starting another execution; retained results are marked stale.

The single Refresh runs button refreshes both the current history page and the selected run's details. It stays disabled while either is loading.

Choose **Download log** for the selected run. `GET /api/v1/runs/{run_id}/log` returns a UTF-8 text attachment containing the overall result, all recorded block details and every persisted event. Export does not use the frontend's 100-event detail limit. Credentials and machine paths stay redacted, including legacy text, and responses use `Cache-Control: no-store`. Runs and artifacts outside the selected workspace are unavailable through the UI/API.

The immediate execution result and historical result use `frontend/src/RunResult.tsx`. Only the historical result displays Download log, so the single button always downloads the selected run. Download errors appear alongside that retryable button. Unknown measurements stay distinct from zero. Output inspection retains the existing governed artifact query behavior.

Only Parquet outputs offer in-app row inspection. CSV outputs show their saved file reference and explain how to view the file in the workspace or use a Parquet Sink. Rejected inspection requests (422), unavailable files (409), missing artifacts (404), and connection errors have distinct guidance; the possible-replacement hint appears only for unavailable files.

Tests cover selected-run isolation, run pagination, errors and reconnects, failed-block navigation, omitted inline events, downloadable log requests, complete redacted exports, and a real-browser download of a previously selected successful run after a failed run.
