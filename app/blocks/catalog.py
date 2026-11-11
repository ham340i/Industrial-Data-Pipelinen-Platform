# AI contribution: below 50% AI-generated
"""Public discovery endpoint; adding blocks requires explicit registration."""

from fastapi import APIRouter

from app.blocks.contracts import BlockMetadata
from app.blocks.registry import BlockRegistry
from app.blocks.sample import AddConstantBlock
from app.blocks.files import CsvSource, JsonSource, ParquetSource, CsvSink, ParquetSink
from app.blocks.transforms import (
    Aggregate,
    Cast,
    Filter,
    Join,
    RenameColumns,
    SelectColumns,
    Sort,
)
from app.blocks.quality import NullHandling, SchemaValidation, NullCheck, RowCount
from app.blocks.triggers import ManualTrigger, TimerTrigger
from app.execution import Executor


router = APIRouter(prefix="/api/v1/blocks", tags=["blocks"])
registry = BlockRegistry()
# Keep exact-version resolution and metadata for existing saved pipelines.
# The example's descriptor hides it from new authoring choices in the builder.
registry.register(AddConstantBlock())
for block in (
    ManualTrigger(),
    TimerTrigger(),
    CsvSource(),
    JsonSource(),
    ParquetSource(),
    SelectColumns(),
    RenameColumns(),
    Filter(),
    Cast(),
    NullHandling(),
    SchemaValidation(),
    NullCheck(),
    RowCount(),
    Join(),
    Aggregate(),
    Sort(),
    CsvSink(),
    ParquetSink(),
):
    registry.register(block)

# Shared, stateless executor (#29): the registry above is read-only once the
# app has started, so one instance is safe to reuse across requests/timers.
executor = Executor(registry)


@router.get("", response_model=list[BlockMetadata])
def list_blocks() -> list[BlockMetadata]:
    return [BlockMetadata.from_public(item) for item in registry.public_metadata()]
