"""Public discovery endpoint; adding blocks requires explicit registration."""

from fastapi import APIRouter

from app.blocks.contracts import BlockMetadata
from app.blocks.registry import BlockRegistry
from app.blocks.sample import AddConstantBlock

router = APIRouter(prefix="/api/v1/blocks", tags=["blocks"])
registry = BlockRegistry()
registry.register(AddConstantBlock())


@router.get("", response_model=list[BlockMetadata])
def list_blocks() -> list[BlockMetadata]:
    return [BlockMetadata.from_public(item) for item in registry.public_metadata()]
