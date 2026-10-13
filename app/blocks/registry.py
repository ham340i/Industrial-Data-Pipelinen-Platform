"""Explicit registration and exact version resolution; no dynamic imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    BlockMetadata,
    PortValues,
    PreviewLimits,
)
from app.blocks.errors import BlockError


class RegisteredBlock(Protocol):
    @property
    def descriptor(self) -> BlockDescriptor: ...

    @property
    def config_model(self) -> type[BlockConfig]: ...

    def public_metadata(self) -> dict[str, Any]: ...

    def validate(
        self, config: dict[str, Any], inputs: PortValues
    ) -> tuple[BlockConfig, PortValues]: ...

    def run(
        self, config: dict[str, Any], inputs: PortValues, context: BlockContext
    ) -> PortValues: ...

    def preview(
        self,
        config: dict[str, Any],
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits | None = None,
    ) -> PortValues: ...


@dataclass(frozen=True)
class _RegisteredEntry:
    block: RegisteredBlock
    descriptor: BlockDescriptor
    metadata: BlockMetadata
    config_model: type[BlockConfig]


class BlockRegistry:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], _RegisteredEntry] = {}

    def register(self, block: RegisteredBlock) -> None:
        try:
            if not isinstance(block.descriptor, BlockDescriptor):
                raise ValueError("Expected a descriptor")
            descriptor = BlockDescriptor.model_validate(block.descriptor.model_dump())
        except Exception:
            raise BlockError("invalid_block", "Block declaration is invalid.") from None
        if descriptor.sdk_version != 1:
            raise BlockError("incompatible_sdk", "Block requires an unsupported SDK.")
        key = (descriptor.block_id, descriptor.version)
        if key in self._entries:
            raise BlockError(
                "duplicate_block", "Block ID/version is already registered."
            )
        try:
            if not isinstance(block.config_model, type) or not issubclass(
                block.config_model, BlockConfig
            ):
                raise ValueError("Expected an SDK configuration model")
            schema = block.config_model.public_schema()
            if (
                descriptor.supports_preview
                and isinstance(block, Block)
                and (type(block)._preview is Block._preview)
            ):
                raise ValueError("Advertised preview requires an implementation")
            if any(
                not callable(getattr(block, name, None))
                for name in ("validate", "run", "preview", "public_metadata")
            ):
                raise ValueError("Missing block interfaces")
            metadata = BlockMetadata.from_public(block.public_metadata())
            expected = BlockMetadata(**descriptor.model_dump(), config_schema=schema)
            if metadata != expected:
                raise ValueError("Metadata does not match the block declaration")
        except Exception:
            raise BlockError(
                "invalid_block", "Block public contract is invalid."
            ) from None
        # No state is changed until the complete public contract has passed.
        self._entries[key] = _RegisteredEntry(
            block, descriptor, metadata, block.config_model
        )

    def resolve(self, block_id: str, version: str) -> RegisteredBlock:
        entry = self._entries.get((block_id, version))
        if entry is not None:
            try:
                current = BlockDescriptor.model_validate(
                    entry.block.descriptor.model_dump()
                )
                if (
                    current != entry.descriptor
                    or entry.block.config_model is not entry.config_model
                ):
                    raise ValueError("Registered declaration changed")
            except Exception:
                raise BlockError(
                    "invalid_block", "Registered block declaration changed."
                ) from None
            return entry.block
        if any(key[0] == block_id for key in self._entries):
            raise BlockError(
                "version_unavailable", "Requested block version is unavailable."
            )
        raise BlockError("block_unavailable", "Requested block is unavailable.")

    def public_metadata(self) -> list[dict[str, Any]]:
        return [
            self._entries[key].metadata.model_dump(mode="json")
            for key in sorted(self._entries)
        ]
