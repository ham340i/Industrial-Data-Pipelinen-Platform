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


router = APIRouter(prefix="/api/v1/blocks", tags=["blocks"])
registry = BlockRegistry()
registry.register(AddConstantBlock())
for block in (
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


@router.get("", response_model=list[BlockMetadata])
def list_blocks() -> list[BlockMetadata]:
    return [BlockMetadata.from_public(item) for item in registry.public_metadata()]
