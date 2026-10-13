"""Execution boundary: config, ports, lifecycle, preview and public failures."""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError

from app.blocks.context import BlockContext, BlockEvent, EventKind
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    BlockMetadata,
    ControlSignal,
    Payload,
    Port,
    PortValues,
    PreviewLimits,
    PublicValueError,
    Table,
    schemas_compatible,
    require_public_json,
)
from app.blocks.errors import BlockError


class Block[ConfigT: BlockConfig](ABC):
    descriptor: BlockDescriptor
    config_model: type[ConfigT]

    def public_metadata(self) -> dict[str, Any]:
        """Publish descriptors/schema only, never instance state or context."""
        descriptor = self._checked_descriptor()
        try:
            metadata = BlockMetadata(
                **descriptor.model_dump(),
                config_schema=self.config_model.public_schema(),
            )
            return metadata.model_dump(mode="json")
        except Exception:
            raise BlockError(
                "invalid_block", "Block public metadata is invalid."
            ) from None

    def _checked_descriptor(self) -> BlockDescriptor:
        try:
            if not isinstance(self.descriptor, BlockDescriptor):
                raise ValueError("Expected a block descriptor")
            descriptor = BlockDescriptor.model_validate(self.descriptor.model_dump())
            if not isinstance(self.config_model, type) or not issubclass(
                self.config_model, BlockConfig
            ):
                raise ValueError("Expected an SDK configuration model")
            self.config_model._check_policy()
        except Exception:
            raise BlockError("invalid_block", "Block declaration is invalid.") from None
        if descriptor.sdk_version != 1:
            raise BlockError("incompatible_sdk", "Block requires an unsupported SDK.")
        return descriptor

    def validate_config(self, config: dict[str, Any]) -> ConfigT:
        try:
            require_public_json(config)
            self.config_model._check_policy()
            return self.config_model.model_validate(copy.deepcopy(config))
        except PublicValueError as exc:
            raise BlockError(
                "invalid_config",
                "Configuration must be credential-free JSON.",
                field=exc.field,
            ) from None
        except ValidationError as exc:
            location = exc.errors(include_input=False, include_context=False)[0]["loc"]
            raise BlockError(
                "invalid_config",
                "Block configuration is invalid.",
                field=".".join(str(part) for part in location) or None,
            ) from None
        except (TypeError, ValueError):
            raise BlockError(
                "invalid_config", "Block configuration is invalid."
            ) from None

    def validate(
        self, config: dict[str, Any], inputs: PortValues
    ) -> tuple[ConfigT, PortValues]:
        """Return parsed config and detached inputs without executing or logging."""
        descriptor = self._checked_descriptor()
        return self._prepare(config, inputs, descriptor)

    def _prepare(
        self, config: dict[str, Any], inputs: PortValues, descriptor: BlockDescriptor
    ) -> tuple[ConfigT, PortValues]:
        return self.validate_config(config), self._check_ports(
            descriptor.inputs, inputs, "invalid_inputs"
        )

    def _check_ports(
        self, ports: tuple[Port, ...], values: PortValues, code: str
    ) -> PortValues:
        if not isinstance(values, dict):
            raise BlockError(code, "Port values must be a mapping of declared names.")
        expected = {port.name: port for port in ports}
        if values.keys() - expected.keys():
            raise BlockError(code, "An undeclared port was supplied.")
        checked: PortValues = {}
        for name, port in expected.items():
            items = values.get(name, ())
            if not isinstance(items, tuple):
                raise BlockError(code, "Port values must be tuples.", field=name)
            if (port.required and not items) or (not port.many and len(items) > 1):
                raise BlockError(code, "Port cardinality is invalid.", field=name)
            validated: list[Payload] = []
            for item in items:
                if port.kind == "control":
                    if not isinstance(item, ControlSignal):
                        raise BlockError(code, "Expected a control signal.", field=name)
                    try:
                        signal = ControlSignal.model_validate(item.model_dump())
                    except ValidationError:
                        raise BlockError(
                            code, "Control signal is invalid.", field=name
                        ) from None
                    validated.append(signal)
                else:
                    if not isinstance(item, Table):
                        raise BlockError(code, "Expected a table.", field=name)
                    try:
                        # Recheck and detach nested dictionaries at the boundary.
                        table = Table.model_validate(item.model_dump())
                    except ValidationError:
                        raise BlockError(
                            code, "Table data is invalid.", field=name
                        ) from None
                    assert port.data_schema is not None
                    if not schemas_compatible(table.data_schema, port.data_schema):
                        raise BlockError(
                            code, "Table schema is incompatible.", field=name
                        )
                    validated.append(table)
            checked[name] = tuple(validated)
        return checked

    def _event(
        self,
        context: BlockContext,
        event: EventKind,
        descriptor: BlockDescriptor | None,
        error_code: str | None = None,
    ) -> None:
        if descriptor is None:
            return
        try:
            context.emit(
                BlockEvent(
                    run_id=context.run_id,
                    node_id=context.node_id,
                    block_id=descriptor.block_id,
                    version=descriptor.version,
                    event=event,
                    error_code=error_code,
                )
            )
        except Exception:
            # Logging is observational and must not change execution outcomes.
            pass

    @staticmethod
    def _check_context(context: BlockContext) -> None:
        if not isinstance(context, BlockContext):
            raise BlockError("invalid_context", "Expected an SDK runtime context.")

    def run(
        self, config: dict[str, Any], inputs: PortValues, context: BlockContext
    ) -> PortValues:
        self._check_context(context)
        descriptor = None
        try:
            descriptor = self._checked_descriptor()
            parsed, checked = self._prepare(config, inputs, descriptor)
            self._event(context, "started", descriptor)
            self.before_execute(parsed, checked, context)
            checked = self._check_ports(descriptor.inputs, checked, "invalid_inputs")
            outputs = self._check_ports(
                descriptor.outputs,
                self._execute(parsed, checked, context),
                "invalid_outputs",
            )
            self.after_execute(parsed, outputs, context)
            outputs = self._check_ports(descriptor.outputs, outputs, "invalid_outputs")
            self._event(context, "succeeded", descriptor)
            return outputs
        except BlockError as exc:
            self._event(context, "failed", descriptor, exc.failure.code)
            raise exc.at_node(context.node_id) from None
        except Exception:
            self._event(context, "failed", descriptor, "execution_failed")
            raise BlockError(
                "execution_failed",
                "Block execution failed.",
                node_id=context.node_id,
            ) from None

    def preview(
        self,
        config: dict[str, Any],
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits | None = None,
    ) -> PortValues:
        self._check_context(context)
        descriptor = None
        try:
            descriptor = self._checked_descriptor()
            if not descriptor.supports_preview:
                raise BlockError(
                    "preview_unsupported",
                    descriptor.preview_reason or "Preview is unsupported.",
                )
            try:
                if limits is not None and not isinstance(limits, PreviewLimits):
                    raise ValueError("Expected preview limits")
                budget = PreviewLimits.model_validate(
                    limits.model_dump() if limits is not None else {}
                )
            except (ValueError, TypeError):
                raise BlockError(
                    "invalid_preview_limits", "Preview limits are invalid."
                ) from None
            parsed, checked = self._prepare(config, inputs, descriptor)
            outputs = self._check_ports(
                descriptor.outputs,
                self._preview(parsed, checked, context, budget),
                "invalid_outputs",
            )
            tables = [
                item
                for items in outputs.values()
                for item in items
                if isinstance(item, Table)
            ]
            rows = sum(len(table.rows) for table in tables)
            cells = sum(
                len(table.rows) * len(table.data_schema.columns) for table in tables
            )
            if rows > budget.max_rows or cells > budget.max_cells:
                raise BlockError("preview_limit", "Preview exceeded its output budget.")
            self._event(context, "previewed", descriptor)
            return outputs
        except BlockError as exc:
            self._event(context, "failed", descriptor, exc.failure.code)
            raise exc.at_node(context.node_id) from None
        except Exception:
            self._event(context, "failed", descriptor, "preview_failed")
            raise BlockError(
                "preview_failed", "Block preview failed.", node_id=context.node_id
            ) from None

    def before_execute(
        self, config: ConfigT, inputs: PortValues, context: BlockContext
    ) -> None:
        """Optional lifecycle hook; do not put data-dependent quality checks here."""
        return None

    def after_execute(
        self, config: ConfigT, outputs: PortValues, context: BlockContext
    ) -> None:
        """Optional successful-execution hook."""
        return None

    @abstractmethod
    def _execute(
        self, config: ConfigT, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        """Implement deterministic block behavior for the same inputs/config."""

    def _preview(
        self,
        config: ConfigT,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        # Preview never defaults to execution, which could publish artifacts.
        raise BlockError("preview_unsupported", "No preview implementation exists.")
