# AI contribution: 50% or more AI-generated
"""Synthetic blocks and seeding helpers shared by the #27 telemetry tests."""

from typing import Any, cast
from uuid import uuid4

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    ControlSignal,
    Port,
    PortValues,
    Scalar,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry
from app.blocks.sample import VALUE_SCHEMA
from app.execution import Cancellation, Executor
from app.metadata.database import Database
from app.metadata.models import Pipeline, PipelineRevision, Project

SECRET_REASON = "Cannot open /home/alice/plant/secret.csv with password=hunter2"
TABLE = (Port(name="table", data_schema=VALUE_SCHEMA),)
SIGNAL = (Port(name="signal", kind="control"),)


def descriptor(block_id: str, block_type: str, **ports: Any) -> BlockDescriptor:
    return BlockDescriptor(
        block_id=block_id,
        version="1",
        block_type=block_type,  # type: ignore[arg-type]
        name=block_id,
        category="test",
        **ports,
    )


class Source(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = descriptor("test.source", "source", outputs=TABLE)
    rows: tuple[dict[str, Scalar], ...] = ({"value": 1}, {"value": 2})

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"table": (Table(data_schema=VALUE_SCHEMA, rows=self.rows),)}


class EmptySource(Source):
    descriptor = descriptor("test.empty", "source", outputs=TABLE)
    rows = ()


class Double(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = descriptor("test.double", "transform", inputs=TABLE, outputs=TABLE)

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = inputs["table"][0]
        assert isinstance(table, Table)
        rows: tuple[dict[str, Scalar], ...] = tuple(
            {"value": cast(int, row["value"]) * 2} for row in table.rows
        )
        return {"table": (Table(data_schema=VALUE_SCHEMA, rows=rows),)}


class Fail(Double):
    """Fails with a reason that leaks a path and a password if not redacted."""

    descriptor = descriptor("test.fail", "transform", inputs=TABLE, outputs=TABLE)

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        raise BlockError("source_unreadable", SECRET_REASON)


class Trigger(Block[BlockConfig]):
    """A one-node, no-edge graph: emits only a ControlSignal, never a Table."""

    config_model = BlockConfig
    descriptor = descriptor("test.trigger", "trigger", outputs=SIGNAL)

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"signal": (ControlSignal(),)}


class Sink(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = descriptor("test.sink", "sink", inputs=TABLE)

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {}


class Cancel(Double):
    """Requests cancellation mid-run, as an operator stop would."""

    descriptor = descriptor("test.cancel", "transform", inputs=TABLE, outputs=TABLE)
    token: Cancellation | None = None

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        assert self.token is not None
        self.token.cancel()
        return super()._execute(config, inputs, context)


def executor(cancel: Cancel | None = None) -> Executor:
    registry = BlockRegistry()
    for block in (
        Source(),
        EmptySource(),
        Double(),
        Fail(),
        Sink(),
        Trigger(),
        cancel or Cancel(),
    ):
        registry.register(block)
    return Executor(registry)


def chain(*blocks: str) -> dict[str, Any]:
    """Linear definition n0 -> n1 -> ... using the given block IDs."""
    nodes = [
        {"id": f"n{i}", "block_id": block, "block_version": "1"}
        for i, block in enumerate(blocks)
    ]
    edges = [
        {
            "id": f"e{i}",
            "source": {"node_id": f"n{i}", "port": "table"},
            "target": {"node_id": f"n{i + 1}", "port": "table"},
        }
        for i in range(len(blocks) - 1)
    ]
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def seed_revision(db: Database, definition: dict[str, Any]) -> str:
    """Persist a project, pipeline and revision 1; returns the revision ID."""
    with db.transaction(write=True) as session:
        project = Project(name="Telemetry")
        session.add(project)
        session.flush()
        pipeline = Pipeline(project_id=project.id, name=f"p-{uuid4().hex[:8]}")
        session.add(pipeline)
        session.flush()
        revision = PipelineRevision(
            pipeline_id=pipeline.id, revision=1, definition=definition
        )
        session.add(revision)
        session.flush()
        return revision.id
