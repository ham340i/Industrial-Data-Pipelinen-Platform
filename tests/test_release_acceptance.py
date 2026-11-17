# AI contribution: 50% or more AI-generated
"""The Release 1 candidate scenario against the real API and engine (#36).

``scripts/release_acceptance.py`` is what the Compose smoke and demo commands
run over HTTP. Driving it here through TestClient keeps its graph, oracle and
failure handling covered by backend CI, where Docker is not required.
"""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from scripts.release_acceptance import (
    EXPECTED_ROWS,
    AcceptanceError,
    Json,
    Send,
    check_rows,
    folder_writer,
    http_sender,
    run_acceptance,
    verify_absent,
    verify_evidence,
)


def client_sender(client: TestClient) -> Send:
    def send(method: str, path: str, body: Json | None) -> tuple[int, Any]:
        response = client.request(method, "/api/v1" + path, json=body)
        return response.status_code, response.json()

    return send


@pytest.fixture
def send(client: TestClient) -> Send:
    return client_sender(client)


def test_release_scenario_runs_twice_and_matches_the_oracle(send: Send, tmp_path: Path):
    evidence = run_acceptance(send, folder_writer(tmp_path / "workspace"))

    assert evidence["rows"] == EXPECTED_ROWS
    assert len(set(evidence["run_ids"])) == 2
    verify_evidence(send, evidence)


def test_reopened_evidence_detects_a_missing_project(send: Send, tmp_path: Path):
    evidence = run_acceptance(send, folder_writer(tmp_path / "workspace"))
    missing = dict(evidence, project_id="00000000-0000-4000-8000-000000000000")

    with pytest.raises(AcceptanceError, match="expected HTTP 200, got 404"):
        verify_evidence(send, missing)
    verify_absent(send, missing)


def test_absent_check_fails_while_the_project_still_exists(send: Send, tmp_path: Path):
    evidence = run_acceptance(send, folder_writer(tmp_path / "workspace"))

    with pytest.raises(AcceptanceError, match="expected HTTP 404, got 200"):
        verify_absent(send, evidence)


def test_missing_input_fails_the_scenario_instead_of_passing(
    send: Send, tmp_path: Path
):
    def drop_sqlite(project_id: str, relative: str, data: bytes) -> None:
        if not relative.endswith(".sqlite3"):
            folder_writer(tmp_path / "workspace")(project_id, relative, data)

    with pytest.raises(AcceptanceError, match="ended failed"):
        run_acceptance(send, drop_sqlite)


def test_rows_differing_from_the_oracle_are_reported(send: Send):
    def fake(method: str, path: str, body: Json | None) -> tuple[int, Any]:
        return 200, {"columns": ["label", "total"], "rows": [["A", 31], ["B", 50]]}

    with pytest.raises(AcceptanceError, match="differ from the oracle"):
        check_rows(fake, "artifact")


@pytest.mark.parametrize(
    "url", ["http://example.com:8000", "https://127.0.0.1:8000", "http://10.0.0.5:80"]
)
def test_http_sender_refuses_non_loopback_targets(url: str):
    with pytest.raises(AcceptanceError, match="loopback"):
        http_sender(url)
