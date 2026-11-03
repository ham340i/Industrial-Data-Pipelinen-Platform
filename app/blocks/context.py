"""Runtime-only services. Context is deliberately not a serializable model."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.blocks.contracts import Contract, NonBlank
from app.blocks.errors import BlockError, QualityDiagnostic

EventKind = Literal["started", "succeeded", "failed", "previewed", "quality"]


class BlockEvent(Contract):
    run_id: NonBlank
    node_id: NonBlank
    block_id: NonBlank
    version: NonBlank
    event: EventKind
    # Fixed event codes only: no config, table values or exception text.
    error_code: NonBlank | None = None
    diagnostics: tuple[QualityDiagnostic, ...] = ()


@dataclass(frozen=True)
class BlockContext:
    run_id: str
    node_id: str
    log_sink: Callable[[BlockEvent], None] | None = field(default=None, repr=False)
    resolve_resource: Callable[[str], Path] | None = field(default=None, repr=False)
    workspace_root: Path | None = field(default=None, repr=False)
    is_cancelled: Callable[[], bool] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.workspace_root is not None and not isinstance(
            self.workspace_root, Path
        ):
            raise BlockError(
                "invalid_context", "Workspace root must be a runtime path."
            )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.run_id, self.node_id)
        ):
            raise BlockError(
                "invalid_context", "Run and node identities must not be blank."
            )
        if any(
            service is not None and not callable(service)
            for service in (self.log_sink, self.resolve_resource, self.is_cancelled)
        ):
            raise BlockError("invalid_context", "Context services must be callable.")

    def check_cancelled(self) -> None:
        """Cooperative checkpoint for long-running blocks."""
        if self.is_cancelled is not None and self.is_cancelled():
            raise BlockError(
                "cancelled", "Execution was cancelled.", node_id=self.node_id
            )

    def emit(self, event: BlockEvent) -> None:
        if self.log_sink is not None:
            try:
                self.log_sink(event)
            except Exception:
                # A log callback must not fail a block invocation.
                pass
