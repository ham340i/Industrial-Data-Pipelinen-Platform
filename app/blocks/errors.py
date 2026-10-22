"""SDK failures carry public context, never raw exceptions or input values."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.blocks.contracts import Contract, NonBlank


class QualityDiagnostic(Contract):
    """Bounded structural evidence; never store cell or fill values here."""

    code: NonBlank
    status: Literal["pass", "fail", "warning"]
    column: NonBlank | None = None
    observed: int = Field(default=0, ge=0)
    minimum: int | None = Field(default=None, ge=0)
    maximum: int | None = Field(default=None, ge=0)
    expected_type: NonBlank | None = None
    actual_type: NonBlank | None = None
    row_indices: tuple[int, ...] = Field(default=(), max_length=20)


class BlockFailure(Contract):
    code: NonBlank = Field(min_length=1)
    reason: NonBlank = Field(min_length=1)
    node_id: NonBlank | None = None
    field: NonBlank | None = None
    diagnostics: tuple[QualityDiagnostic, ...] = ()


class BlockError(RuntimeError):
    def __init__(
        self,
        code: str,
        reason: str,
        *,
        node_id: str | None = None,
        field: str | None = None,
        diagnostics: tuple[QualityDiagnostic, ...] = (),
    ) -> None:
        self.failure = BlockFailure(
            code=code,
            reason=reason,
            node_id=node_id,
            field=field,
            diagnostics=diagnostics,
        )
        super().__init__(reason)

    def at_node(self, node_id: str) -> BlockError:
        return BlockError(
            self.failure.code,
            self.failure.reason,
            node_id=node_id,
            field=self.failure.field,
            diagnostics=self.failure.diagnostics,
        )
