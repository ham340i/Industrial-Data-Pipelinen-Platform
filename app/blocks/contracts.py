"""SDK v1 public contracts, independent of the API and database."""

from __future__ import annotations

import math
import json
import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    AfterValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

Scalar = str | int | float | bool | None


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Public identifiers and descriptions must not be blank")
    return value


NonBlank = Annotated[str, AfterValidator(_nonblank)]

_CREDENTIAL_FIELDS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secrets",
        "credential",
        "credentials",
        "token",
        "accesstoken",
        "refreshtoken",
        "apikey",
        "connectionstring",
        "dsn",
        "username",
    }
)


class PublicValueError(ValueError):
    def __init__(self, field: str | None = None) -> None:
        self.field = field
        super().__init__("Public values must be finite, credential-free JSON.")


def require_public_json(value: object) -> None:
    """Check original Python values: JSON serialization alone coerces some types.

    Known credential keys are forbidden, including in schema defaults. This is
    not a detector for arbitrary secret strings under otherwise public names.
    """
    active: set[int] = set()

    def visit(item: object, path: tuple[str, ...]) -> None:
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise PublicValueError(".".join(path) or None)
            return
        if isinstance(item, (dict, list)):
            identity = id(item)
            if identity in active:
                raise PublicValueError(".".join(path) or None)
            active.add(identity)
            try:
                if isinstance(item, dict):
                    for key, child in item.items():
                        if not isinstance(key, str):
                            raise PublicValueError()
                        child_path = (*path, key)
                        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
                        if normalized in _CREDENTIAL_FIELDS:
                            raise PublicValueError(".".join(child_path))
                        visit(child, child_path)
                else:
                    for index, child in enumerate(item):
                        visit(child, (*path, str(index)))
            finally:
                active.remove(identity)
            return
        raise PublicValueError(".".join(path) or None)

    visit(value, ())
    # Confirm the checked values can actually be exported by the JSON encoder.
    json.dumps(value, allow_nan=False)


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, validate_default=True
    )


class BlockConfig(Contract):
    """Base for public configuration; runtime objects/credentials stay in context."""

    @model_validator(mode="before")
    @classmethod
    def public_input(cls, value: Any) -> Any:
        require_public_json(value)
        return value

    @model_validator(mode="after")
    def public_defaults(self) -> BlockConfig:
        require_public_json(self.model_dump(mode="python"))
        return self

    @classmethod
    def _check_policy(cls) -> None:
        required_options = {
            "extra": "forbid",
            "frozen": True,
            "strict": True,
            "validate_default": True,
        }
        if any(
            cls.model_config.get(key) != value
            for key, value in required_options.items()
        ):
            raise ValueError("Block configuration must preserve the SDK model policy")

    @classmethod
    def public_schema(cls) -> dict[str, Any]:
        cls._check_policy()
        schema = cls.model_json_schema()
        require_public_json(schema)
        defaults: dict[str, Any] = {}
        for name, definition in cls.model_fields.items():
            if definition.is_required():
                continue
            default = definition.get_default(
                call_default_factory=True, validated_data=defaults
            )
            checked = TypeAdapter(definition.rebuild_annotation()).validate_python(
                default, strict=True
            )
            require_public_json(checked)
            defaults[name] = checked
        try:
            cls.model_validate({})
        except ValidationError as exc:
            errors = exc.errors(include_input=False, include_context=False)
            if any(error["type"] != "missing" for error in errors):
                raise
            if definition.validate_default is False:
                raise ValueError("Configuration defaults must remain validated") from exc
        return schema


class Column(Contract):
    name: NonBlank = Field(min_length=1)
    dtype: Literal["string", "integer", "number", "boolean"]
    nullable: bool = False


class DataSchema(Contract):
    columns: tuple[Column, ...]
    allow_extra_columns: bool = False

    @model_validator(mode="after")
    def unique_columns(self) -> DataSchema:
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("Column names must be unique")
        return self


class Table(Contract):
    """Typed Python table with fully declared columns, even when empty."""

    data_schema: DataSchema
    rows: tuple[dict[str, Scalar], ...]

    @model_validator(mode="after")
    def validate_rows(self) -> Table:
        names = {column.name for column in self.data_schema.columns}
        for row in self.rows:
            if set(row) != names:
                raise ValueError("Every row must match its declared columns")
            for column in self.data_schema.columns:
                value = row[column.name]
                if value is None:
                    if column.nullable:
                        continue
                    raise ValueError("Null in a non-nullable column")
                matches = {
                    "string": type(value) is str,
                    "integer": type(value) is int,
                    "number": type(value) in (int, float),
                    "boolean": type(value) is bool,
                }
                if not matches[column.dtype]:
                    raise ValueError("Value does not match its declared type")
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Non-finite numbers are unsupported")
        return self


class ControlSignal(Contract):
    """Control has no invented tabular rows or arbitrary payload."""

    kind: Literal["trigger"] = "trigger"


class Port(Contract):
    name: NonBlank = Field(min_length=1)
    kind: Literal["data", "control"] = "data"
    required: bool = True
    many: bool = False
    data_schema: DataSchema | None = None

    @model_validator(mode="after")
    def schema_matches_kind(self) -> Port:
        if (self.kind == "data") != (self.data_schema is not None):
            raise ValueError("Only data ports must declare a data schema")
        return self


class BlockDescriptor(Contract):
    sdk_version: int = Field(default=1, ge=1)
    block_id: NonBlank = Field(min_length=1, max_length=128)
    version: NonBlank = Field(min_length=1, max_length=32)
    block_type: Literal["trigger", "source", "transform", "quality", "sink"]
    name: NonBlank = Field(min_length=1, max_length=128)
    category: NonBlank = Field(min_length=1, max_length=64)
    inputs: tuple[Port, ...] = ()
    outputs: tuple[Port, ...] = ()
    supports_preview: bool = False
    preview_reason: NonBlank | None = "Preview is not supported by this block."

    @model_validator(mode="after")
    def validate_descriptor(self) -> BlockDescriptor:
        for ports in (self.inputs, self.outputs):
            names = [port.name for port in ports]
            if len(names) != len(set(names)):
                raise ValueError("Port names must be unique within each direction")
        if not self.block_id.strip() or not self.version.strip():
            raise ValueError("Block identity must not be blank")
        if self.supports_preview:
            if self.preview_reason is not None or self.block_type == "sink":
                raise ValueError("Preview requires no unsupported reason or sink")
        elif not self.preview_reason or not self.preview_reason.strip():
            raise ValueError("Unsupported preview must supply a reason")
        if self.block_type == "trigger" and any(
            port.kind != "control" for port in self.outputs
        ):
            raise ValueError("Triggers emit control signals")
        return self


class PreviewLimits(Contract):
    max_rows: int = Field(default=20, ge=1, le=1000)
    max_cells: int = Field(default=2000, ge=1, le=10000)


class BlockMetadata(BlockDescriptor):
    config_schema: dict[str, Any]

    @field_validator("config_schema", mode="before")
    @classmethod
    def public_configuration_schema(cls, value: Any) -> Any:
        require_public_json(value)
        return value

    @classmethod
    def from_public(cls, value: object) -> BlockMetadata:
        """Read the actual public JSON shape, rejecting handles and coercions."""
        require_public_json(value)
        return cls.model_validate_json(json.dumps(value, allow_nan=False))


Payload = Table | ControlSignal
# Tuples represent cardinality consistently, including single-valued ports.
PortValues = dict[str, tuple[Payload, ...]]


def schemas_compatible(produced: DataSchema, expected: DataSchema) -> bool:
    """Exact types and safe nullability; widening rules are a later decision."""
    actual = {column.name: column for column in produced.columns}
    required = {column.name: column for column in expected.columns}
    if not required.keys() <= actual.keys():
        return False
    if not expected.allow_extra_columns and actual.keys() != required.keys():
        return False
    return all(
        actual[name].dtype == column.dtype
        and (column.nullable or not actual[name].nullable)
        for name, column in required.items()
    )

def ports_compatible(output: Port, input: Port) -> bool:
    if output.kind != input.kind:
        return False
    if output.kind == "control":
        return True
    assert output.data_schema != None and input.data_schema != None
    if output.data_schema.allow_extra_columns and not input.data_schema.allow_extra_columns:
        return False
    return schemas_compatible(output.data_schema, input.data_schema)
