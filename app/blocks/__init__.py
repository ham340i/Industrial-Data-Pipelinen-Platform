"""Headless Block SDK. Importing it performs no registration or I/O."""

from app.blocks.base import Block
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    BlockMetadata,
    Column,
    ControlSignal,
    DataSchema,
    Port,
    PortValues,
    PreviewLimits,
    Table,
    ports_compatible,
)
from app.blocks.errors import BlockError, BlockFailure
from app.blocks.registry import BlockRegistry

__all__ = [
    "Block",
    "BlockConfig",
    "BlockContext",
    "BlockDescriptor",
    "BlockError",
    "BlockEvent",
    "BlockFailure",
    "BlockMetadata",
    "BlockRegistry",
    "Column",
    "ControlSignal",
    "DataSchema",
    "Port",
    "PortValues",
    "PreviewLimits",
    "Table",
    "ports_compatible",
]
