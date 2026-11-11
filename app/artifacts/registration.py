"""Persist trusted file-sink outputs after their atomic publication."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.blocks.contracts import DataSchema
from app.blocks.files import ARTIFACT_SCHEMA
from app.execution import ExecutionContext, Frame
from app.metadata.models import OutputEndpoint

SINK_FORMATS = {"sink.csv": "csv", "sink.parquet": "parquet"}


def sink_format(block_id: str) -> str | None:
    """Return the governed format for a production file-sink block."""
    return SINK_FORMATS.get(block_id)


def _artifact_row(frame: Frame) -> dict[str, Any]:
    """Validate and detach the bounded, one-row sink metadata contract."""
    table = frame.to_table()
    if table.data_schema != ARTIFACT_SCHEMA or len(table.rows) != 1:
        raise ValueError("File sink returned invalid artifact metadata")
    return dict(table.rows[0])


def register_published_artifacts(
    session: Session,
    run_id: str,
    node_blocks: Mapping[str, str],
    context: ExecutionContext,
) -> None:
    """Register completed production file sinks without reading artifact bytes."""
    for node_id, block_id in node_blocks.items():
        expected_format = sink_format(block_id)
        if expected_format is None or context.node_states.get(node_id) != "completed":
            continue
        values = context.outputs.get(node_id, {}).get("artifact", ())
        if len(values) != 1 or not isinstance(values[0], Frame):
            raise ValueError("Completed file sink is missing artifact metadata")
        row = _artifact_row(values[0])
        if row["format"] != expected_format:
            raise ValueError("File sink artifact format does not match its block")
        schema = DataSchema.model_validate_json(row["schema_json"])
        session.add(
            OutputEndpoint(
                run_id=run_id,
                node_id=node_id,
                name="artifact",
                format=expected_format,
                artifact_ref=row["location"],
                row_count=row["row_count"],
                schema_json=schema.model_dump(mode="json"),
            )
        )
