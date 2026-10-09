"""SDK failures carry public context, never raw exceptions or input values."""

from __future__ import annotations

from pydantic import Field

from app.blocks.contracts import Contract, NonBlank


class BlockFailure(Contract):
    code: NonBlank = Field(min_length=1)
    reason: NonBlank = Field(min_length=1)
    node_id: NonBlank | None = None
    field: NonBlank | None = None


class BlockError(RuntimeError):
    def __init__(
        self,
        code: str,
        reason: str,
        *,
        node_id: str | None = None,
        field: str | None = None,
    ) -> None:
        self.failure = BlockFailure(
            code=code, reason=reason, node_id=node_id, field=field
        )
        super().__init__(reason)

    def at_node(self, node_id: str) -> BlockError:
        return BlockError(
            self.failure.code,
            self.failure.reason,
            node_id=node_id,
            field=self.failure.field,
        )
