"""SDK contract and synthetic integration checks for issue #8."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ConfigDict, Field, ValidationError, field_validator

from app.blocks import (
    Block,
    BlockConfig,
    BlockContext,
    BlockDescriptor,
    BlockError,
    BlockEvent,
    BlockFailure,
    BlockMetadata,
    BlockRegistry,
    Column,
    ControlSignal,
    DataSchema,
    Port,
    PortValues,
    PreviewLimits,
    Table,
    ports_compatible,
)
from app.blocks.sample import AddConstantBlock, AddConstantConfig, VALUE_SCHEMA

INVALID_CONFIG_CASES: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "fixtures" / "blocks" / "invalid_configs.json").read_text(
        encoding="utf-8"
    )
)["cases"]


def input_values(*values: int) -> PortValues:
    return {
        "table": (
            Table(data_schema=VALUE_SCHEMA, rows=tuple({"value": n} for n in values)),
        )
    }


def test_registered_block_executes_golden_fixture_and_logs():
    fixture_path = Path(__file__).parent / "fixtures" / "blocks" / "add_constant.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    table = Table(data_schema=VALUE_SCHEMA, rows=tuple(fixture["input_rows"]))
    registry = BlockRegistry()
    registry.register(AddConstantBlock())
    events: list[BlockEvent] = []
    context = BlockContext("synthetic-run", "node-1", log_sink=events.append)
    block = registry.resolve("synthetic.add_constant", "1.0.0")

    outputs = block.run(fixture["config"], {"table": (table,)}, context)
    result = outputs["table"][0]
    assert isinstance(result, Table)
    assert list(result.rows) == fixture["expected_rows"]
    assert result.data_schema == VALUE_SCHEMA
    assert block.run(fixture["config"], {"table": (table,)}, context) == outputs
    assert [event.event for event in events] == [
        "started",
        "succeeded",
        "started",
        "succeeded",
    ]
    assert all(event.node_id == "node-1" for event in events)
    assert all(event.version == "1.0.0" for event in events)


def test_registry_metadata_roundtrip_and_detached_export():
    registry = BlockRegistry()
    registry.register(AddConstantBlock())
    metadata = registry.public_metadata()[0]
    assert json.loads(json.dumps(metadata, allow_nan=False)) == metadata
    descriptor_data = {
        key: value for key, value in metadata.items() if key != "config_schema"
    }
    descriptor = BlockDescriptor.model_validate_json(json.dumps(descriptor_data))
    assert descriptor == AddConstantBlock.descriptor
    assert "amount" in metadata["config_schema"]["properties"]
    assert metadata["supports_preview"] is True
    metadata["config_schema"]["properties"].clear()
    assert "amount" in registry.public_metadata()[0]["config_schema"]["properties"]
    forbidden = {"rows", "credentials", "resolve_resource", "log_sink"}
    assert forbidden.isdisjoint(metadata)


@pytest.mark.parametrize(
    "config, field",
    [
        ({"amount": "synthetic-secret"}, "amount"),
        ({"amount": 1001}, "amount"),
        ({"password": "synthetic-secret"}, "password"),
    ],
)
def test_invalid_config_is_structured_without_echoing_values(
    config: dict[str, Any], field: str
):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().run(config, input_values(1), BlockContext("run", "node"))
    failure = caught.value.failure
    assert failure.code == "invalid_config"
    assert failure.node_id == "node" and failure.field == field
    assert "synthetic-secret" not in failure.model_dump_json()
    assert BlockFailure.model_validate_json(failure.model_dump_json()) == failure


def test_config_defaults_and_json_roundtrip():
    config = AddConstantBlock().validate_config({})
    assert config.amount == 1
    assert AddConstantConfig.model_validate_json(config.model_dump_json()) == config


def test_validation_does_not_execute_and_detaches_inputs():
    class MustNotExecute(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            raise AssertionError("Validation must not execute")

    inputs = input_values(1)
    config, checked = MustNotExecute().validate({}, inputs)
    assert config.amount == 1 and checked == inputs
    table = checked["table"][0]
    original = inputs["table"][0]
    assert isinstance(table, Table) and isinstance(original, Table)
    table.rows[0]["value"] = 100
    assert original.rows[0]["value"] == 1


def test_port_rejects_a_valid_table_with_the_wrong_schema():
    other_schema = DataSchema(columns=(Column(name="other", dtype="integer"),))
    table = Table(data_schema=other_schema, rows=({"other": 1},))
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().validate({}, {"table": (table,)})
    assert caught.value.failure.code == "invalid_inputs"
    assert caught.value.failure.field == "table"


def test_extra_column_and_type_compatibility_rules():
    extra = DataSchema(
        columns=(
            Column(name="value", dtype="integer"),
            Column(name="label", dtype="string"),
        )
    )
    number = DataSchema(columns=(Column(name="value", dtype="number"),))
    assert not ports_compatible(
        Port(name="out", data_schema=extra), Port(name="in", data_schema=VALUE_SCHEMA)
    )
    assert ports_compatible(
        Port(name="out", data_schema=extra),
        Port(
            name="in",
            data_schema=DataSchema(
                columns=VALUE_SCHEMA.columns, allow_extra_columns=True
            ),
        ),
    )
    assert not ports_compatible(
        Port(name="out", data_schema=number), Port(name="in", data_schema=VALUE_SCHEMA)
    )
    assert not ports_compatible(
            Port(name="out", data_schema=DataSchema(columns=VALUE_SCHEMA.columns,
                allow_extra_columns=True)), Port(name="in", data_schema=VALUE_SCHEMA))

def test_custom_default_validator_with_required_field():
    class BadDefault(AddConstantConfig):
        resource_id: str
        amount: int = 0

        @field_validator("amount")
        @classmethod
        def positive_amount(cls, value: int) -> int:
            if value <= 0:
                raise ValueError("Amount must be positive")
            return value

    class BadBlock(AddConstantBlock):
        config_model = BadDefault

    assert_invalid_registration(BadBlock())

@pytest.mark.parametrize("value", [True, "1", None, 1.5])
def test_table_checks_actual_row_types(value: Any):
    with pytest.raises(ValidationError):
        Table(data_schema=VALUE_SCHEMA, rows=({"value": value},))


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_table_rejects_nonfinite_numbers(value: float):
    schema = DataSchema(columns=(Column(name="value", dtype="number"),))
    with pytest.raises(ValidationError):
        Table(data_schema=schema, rows=({"value": value},))


def test_schema_compatibility_preserves_nullability_and_control_semantics():
    strict = Port(name="table", data_schema=VALUE_SCHEMA)
    nullable = Port(
        name="table",
        data_schema=DataSchema(
            columns=(Column(name="value", dtype="integer", nullable=True),)
        ),
    )
    control = Port(name="start", kind="control")
    assert ports_compatible(strict, nullable)
    assert not ports_compatible(nullable, strict)
    assert not ports_compatible(control, strict)
    assert ports_compatible(control, control)
    with pytest.raises(ValidationError):
        Port(name="start", kind="control", data_schema=VALUE_SCHEMA)


@pytest.mark.parametrize(
    "inputs",
    [{}, {"table": ()}, {"table": (ControlSignal(),)}, {"unknown": (ControlSignal(),)}],
)
def test_invalid_input_ports(inputs: PortValues):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().run({}, inputs, BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"


def test_single_port_rejects_multiple_tables():
    values = input_values(1)
    values["table"] = values["table"] * 2
    with pytest.raises(BlockError, match="cardinality"):
        AddConstantBlock().run({}, values, BlockContext("run", "node"))


def test_boundary_rechecks_mutated_nested_rows():
    inputs = input_values(1)
    table = inputs["table"][0]
    assert isinstance(table, Table)
    table.rows[0]["value"] = "bad"
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().run({}, inputs, BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"


def test_preview_obeys_combined_row_and_cell_budget():
    events: list[BlockEvent] = []
    outputs = AddConstantBlock().preview(
        {},
        input_values(1, 2, 3, 4),
        BlockContext("run", "node", events.append),
        PreviewLimits(max_rows=3, max_cells=2),
    )
    table = outputs["table"][0]
    assert isinstance(table, Table)
    assert table.rows == ({"value": 2}, {"value": 3})
    assert [event.event for event in events] == ["previewed"]


def test_unsupported_preview_never_executes():
    class Unsupported(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "supports_preview": False,
                "preview_reason": "No preview implementation.",
            }
        )

        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            raise AssertionError("Execution must not run")

    with pytest.raises(BlockError) as caught:
        Unsupported().preview({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "preview_unsupported"


def test_preview_rejects_implementation_exceeding_budget():
    class Unbounded(AddConstantBlock):
        def _preview(
            self,
            config: AddConstantConfig,
            inputs: PortValues,
            context: BlockContext,
            limits: PreviewLimits,
        ) -> PortValues:
            return self._execute(config, inputs, context)

    with pytest.raises(BlockError) as caught:
        Unbounded().preview(
            {},
            input_values(1, 2),
            BlockContext("run", "node"),
            PreviewLimits(max_rows=1),
        )
    assert caught.value.failure.code == "preview_limit"


def test_missing_versions_and_duplicate_registration():
    registry = BlockRegistry()
    registry.register(AddConstantBlock())
    with pytest.raises(BlockError) as duplicate:
        registry.register(AddConstantBlock())
    assert duplicate.value.failure.code == "duplicate_block"
    with pytest.raises(BlockError) as unavailable:
        registry.resolve("synthetic.add_constant", "2.0.0")
    assert unavailable.value.failure.code == "version_unavailable"
    with pytest.raises(BlockError) as missing:
        registry.resolve("unknown", "1.0.0")
    assert missing.value.failure.code == "block_unavailable"


def test_incompatible_sdk_is_rejected():
    block = AddConstantBlock()
    block.descriptor = block.descriptor.model_copy(update={"sdk_version": 2})
    with pytest.raises(BlockError) as caught:
        BlockRegistry().register(block)
    assert caught.value.failure.code == "incompatible_sdk"


def test_unexpected_exception_and_logs_do_not_expose_internal_details():
    class Failing(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            raise RuntimeError("synthetic-secret and private-row")

    events: list[BlockEvent] = []
    with pytest.raises(BlockError) as caught:
        Failing().run({}, input_values(1), BlockContext("run", "node", events.append))
    assert caught.value.failure.code == "execution_failed"
    public = caught.value.failure.model_dump_json() + json.dumps(
        [event.model_dump(mode="json") for event in events]
    )
    assert "synthetic-secret" not in public and "private-row" not in public
    assert [event.event for event in events] == ["started", "failed"]


def test_invalid_output_contract_is_rejected():
    class InvalidOutput(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            return {}

    with pytest.raises(BlockError) as caught:
        InvalidOutput().run({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_outputs"


def test_empty_table_retains_schema():
    outputs = AddConstantBlock().run({}, input_values(), BlockContext("run", "node"))
    table = outputs["table"][0]
    assert isinstance(table, Table)
    assert table.rows == () and table.data_schema == VALUE_SCHEMA


@pytest.mark.parametrize("field", ["block_id", "version", "name", "category"])
def test_descriptor_rejects_blank_public_strings(field: str):
    values = AddConstantBlock.descriptor.model_dump()
    values[field] = " \t"
    with pytest.raises(ValidationError):
        BlockDescriptor.model_validate(values)


def test_duplicate_columns_and_ports_are_invalid():
    with pytest.raises(ValidationError):
        DataSchema(columns=VALUE_SCHEMA.columns * 2)
    values = AddConstantBlock.descriptor.model_dump()
    values["inputs"] = values["inputs"] * 2
    with pytest.raises(ValidationError):
        BlockDescriptor.model_validate(values)
    with pytest.raises(ValidationError):
        Column(name=" ", dtype="integer")
    with pytest.raises(ValidationError):
        Port(name=" ", kind="control")


def test_metadata_has_a_typed_json_roundtrip():
    exported = AddConstantBlock().public_metadata()
    metadata = BlockMetadata.from_public(exported)
    assert metadata.block_id == "synthetic.add_constant"
    assert metadata.model_dump(mode="json") == exported
    assert BlockMetadata.model_validate_json(metadata.model_dump_json()) == metadata


def assert_invalid_registration(block: AddConstantBlock) -> None:
    block.descriptor = block.descriptor.model_copy(update={"block_id": "synthetic.bad"})
    registry = BlockRegistry()
    registry.register(AddConstantBlock())
    previous = registry.public_metadata()
    with pytest.raises(BlockError) as caught:
        registry.register(block)
    assert caught.value.failure.code == "invalid_block"
    assert "synthetic-secret" not in caught.value.failure.model_dump_json()
    assert registry.public_metadata() == previous
    with pytest.raises(BlockError) as missing:
        registry.resolve("synthetic.bad", "1.0.0")
    assert missing.value.failure.code == "block_unavailable"


def test_invalid_config_default_fails_registration_without_partial_state():
    class BadDefault(AddConstantConfig):
        amount: int = Field(default=cast(int, "synthetic-secret"))

    class BadBlock(AddConstantBlock):
        config_model = BadDefault

    assert_invalid_registration(BadBlock())


def test_nonjson_factory_default_fails_registration():
    class RuntimeDefault(AddConstantConfig):
        handle: Any = Field(default_factory=object)

    class BadBlock(AddConstantBlock):
        config_model = RuntimeDefault

    assert_invalid_registration(BadBlock())


def test_permissive_configuration_models_are_rejected():
    class Permissive(AddConstantConfig):
        model_config = ConfigDict(extra="allow")

    class BadBlock(AddConstantBlock):
        config_model = Permissive

    assert_invalid_registration(BadBlock())


def test_credential_field_and_default_are_never_published():
    class CredentialConfig(AddConstantConfig):
        password: str = "synthetic-secret"

    class BadBlock(AddConstantBlock):
        config_model = CredentialConfig

    block = BadBlock()
    assert_invalid_registration(block)
    with pytest.raises(BlockError) as caught:
        block.validate_config({})
    assert caught.value.failure.code == "invalid_config"
    assert "synthetic-secret" not in caught.value.failure.model_dump_json()


def test_nested_credential_default_and_alias_are_rejected():
    class NestedDefault(AddConstantConfig):
        options: dict[str, Any] = Field(default={"credentials": "synthetic-secret"})

    class BadNested(AddConstantBlock):
        config_model = NestedDefault

    class CredentialAlias(AddConstantConfig):
        access: str = Field(default="synthetic-secret", alias="API-Key")

    class BadAlias(AddConstantBlock):
        config_model = CredentialAlias

    assert_invalid_registration(BadNested())
    assert_invalid_registration(BadAlias())


def test_public_alias_and_empty_config_string_are_supported():
    class Aliased(AddConstantConfig):
        amount: int = Field(default=1, alias="increment")
        label: str = ""

    class AliasBlock(Block[Aliased]):
        config_model = Aliased
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "supports_preview": False,
                "preview_reason": "Configuration-only example.",
            }
        )

        def _execute(
            self, config: Aliased, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            return inputs

    registry = BlockRegistry()
    block = AliasBlock()
    registry.register(block)
    assert block.validate_config({}).amount == 1
    assert block.validate_config({"increment": 3}).amount == 3


@pytest.mark.parametrize(
    "injection",
    [
        {"credentials": {"password": "synthetic-secret"}},
        {"context": object()},
        {"unexpected": "synthetic-secret"},
        {"name": "different-public-name"},
    ],
)
def test_untrusted_metadata_cannot_override_the_typed_contract(
    injection: dict[str, Any],
):
    class BadMetadata(AddConstantBlock):
        def public_metadata(self) -> dict[str, Any]:
            return super().public_metadata() | injection

    assert_invalid_registration(BadMetadata())


def test_versions_coexist_and_registered_identity_cannot_drift():
    older = AddConstantBlock()
    newer = AddConstantBlock()
    newer.descriptor = newer.descriptor.model_copy(update={"version": "1.1.0"})
    registry = BlockRegistry()
    registry.register(newer)
    registry.register(older)
    assert registry.resolve("synthetic.add_constant", "1.0.0") is older
    assert registry.resolve("synthetic.add_constant", "1.1.0") is newer
    previous = registry.public_metadata()
    assert [item["version"] for item in previous] == ["1.0.0", "1.1.0"]
    older.descriptor = older.descriptor.model_copy(update={"version": "9.0.0"})
    with pytest.raises(BlockError) as caught:
        registry.resolve("synthetic.add_constant", "1.0.0")
    assert caught.value.failure.code == "invalid_block"
    assert registry.public_metadata() == previous


def test_invalid_copied_descriptor_is_checked_at_registration():
    block = AddConstantBlock()
    block.descriptor = block.descriptor.model_copy(update={"name": " "})
    assert_invalid_registration(block)


@pytest.mark.parametrize(
    "config",
    [
        {"amount": float("nan")},
        {"amount": (1,)},
        {1: "non-string-key"},
        {"amount": Path("synthetic.sqlite3")},
        {"options": {"access_token": "synthetic-secret"}},
    ],
)
def test_public_config_rejects_nonjson_or_credential_values(config: Any):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().validate_config(config)
    assert caught.value.failure.code == "invalid_config"
    assert "synthetic-secret" not in caught.value.failure.model_dump_json()


def test_cyclic_config_is_a_structured_failure():
    config: dict[str, Any] = {}
    config["cycle"] = config
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().validate_config(config)
    assert caught.value.failure.code == "invalid_config"


@pytest.mark.parametrize("case", INVALID_CONFIG_CASES, ids=lambda case: case["name"])
def test_negative_contract_fixture(case: dict[str, Any]):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().run(
            case["config"], input_values(1), BlockContext("run", "node")
        )
    assert caught.value.failure.code == "invalid_config"
    assert caught.value.failure.field == case["field"]
    assert caught.value.failure.node_id == "node"


class CardinalityBlock(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="synthetic.cardinality",
        version="1",
        block_type="quality",
        name="Contract test relay",
        category="synthetic",
        inputs=(
            Port(name="tables", required=False, many=True, data_schema=VALUE_SCHEMA),
            Port(name="start", kind="control", required=False, many=True),
        ),
        outputs=(
            Port(name="tables", required=False, many=True, data_schema=VALUE_SCHEMA),
            Port(name="start", kind="control", required=False, many=True),
        ),
    )

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return inputs


def test_optional_ports_and_many_data_control_values():
    block = CardinalityBlock()
    context = BlockContext("run", "node")
    assert block.run({}, {}, context) == {"tables": (), "start": ()}
    table = input_values(1)["table"][0]
    inputs: PortValues = {
        "tables": (table, table),
        "start": (ControlSignal(), ControlSignal()),
    }
    assert block.run({}, inputs, context) == inputs
    assert ControlSignal.model_validate_json('{"kind":"trigger"}') == ControlSignal()


def test_required_many_port_rejects_zero_and_accepts_multiple_values():
    block = CardinalityBlock()
    port = Port(name="tables", many=True, data_schema=VALUE_SCHEMA)
    block.descriptor = block.descriptor.model_copy(update={"inputs": (port,)})
    with pytest.raises(BlockError) as caught:
        block.run({}, {}, BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"
    table = input_values(1)["table"][0]
    assert (
        len(
            block.run({}, {"tables": (table, table)}, BlockContext("run", "node"))[
                "tables"
            ]
        )
        == 2
    )


@pytest.mark.parametrize("inputs", [None, [], {"table": []}, {"table": (object(),)}])
def test_malformed_input_shape_has_an_input_error(inputs: Any):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().run({}, inputs, BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"


@pytest.mark.parametrize("outputs", [None, [], {"table": []}, {"table": (object(),)}])
def test_malformed_output_shape_has_an_output_error(outputs: Any):
    class Malformed(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            return cast(PortValues, outputs)

    with pytest.raises(BlockError) as caught:
        Malformed().run({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_outputs"


def test_unvalidated_control_signal_is_rechecked():
    invalid = ControlSignal.model_construct(kind="invalid")
    with pytest.raises(BlockError) as caught:
        CardinalityBlock().run({}, {"start": (invalid,)}, BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"


def test_execution_lifecycle_order_and_detached_outputs():
    observed: list[str] = []

    class Observed(AddConstantBlock):
        def before_execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> None:
            observed.append("before")

        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            observed.append("execute")
            return super()._execute(config, inputs, context)

        def after_execute(
            self, config: AddConstantConfig, outputs: PortValues, context: BlockContext
        ) -> None:
            observed.append("after")

    inputs = input_values(1)
    outputs = Observed().run({}, inputs, BlockContext("run", "node"))
    assert observed == ["before", "execute", "after"]
    table, original = outputs["table"][0], inputs["table"][0]
    assert isinstance(table, Table) and isinstance(original, Table)
    table.rows[0]["value"] = 999
    assert original.rows[0]["value"] == 1


def test_after_hook_cannot_return_invalid_outputs():
    class Mutating(AddConstantBlock):
        def after_execute(
            self, config: AddConstantConfig, outputs: PortValues, context: BlockContext
        ) -> None:
            table = outputs["table"][0]
            assert isinstance(table, Table)
            table.rows[0]["value"] = "wrong-type"

    events: list[BlockEvent] = []
    with pytest.raises(BlockError) as caught:
        Mutating().run({}, input_values(1), BlockContext("run", "node", events.append))
    assert caught.value.failure.code == "invalid_outputs"
    assert [event.event for event in events] == ["started", "failed"]


def test_before_hook_cannot_bypass_input_validation():
    class Mutating(AddConstantBlock):
        def before_execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> None:
            inputs["table"] = ()

    with pytest.raises(BlockError) as caught:
        Mutating().run({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_inputs"


def test_wrong_output_schema_is_rejected():
    class WrongSchema(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            schema = DataSchema(columns=(Column(name="value", dtype="string"),))
            return {"table": (Table(data_schema=schema, rows=({"value": "1"},)),)}

    with pytest.raises(BlockError) as caught:
        WrongSchema().run({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "invalid_outputs"


@pytest.mark.parametrize("fails", [False, True])
def test_broken_logger_preserves_success_or_original_failure(fails: bool):
    def broken_logger(event: BlockEvent) -> None:
        raise RuntimeError("synthetic-secret")

    class SometimesFailing(AddConstantBlock):
        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            if fails:
                raise BlockError("synthetic_failure", "Synthetic block failed.")
            return super()._execute(config, inputs, context)

    context = BlockContext("run", "node", broken_logger)
    if fails:
        with pytest.raises(BlockError) as caught:
            SometimesFailing().run({}, input_values(1), context)
        assert caught.value.failure.code == "synthetic_failure"
        assert "synthetic-secret" not in caught.value.failure.model_dump_json()
    else:
        table = SometimesFailing().run({}, input_values(1), context)["table"][0]
        assert isinstance(table, Table) and table.rows == ({"value": 2},)


@pytest.mark.parametrize("run_id, node_id", [("", "node"), ("run", " "), (1, "node")])
def test_context_requires_valid_identities(run_id: Any, node_id: Any):
    with pytest.raises(BlockError) as caught:
        BlockContext(run_id, node_id)
    assert caught.value.failure.code == "invalid_context"


def test_invalid_context_callback_is_rejected():
    with pytest.raises(BlockError) as caught:
        BlockContext("run", "node", log_sink=cast(Any, "not-callable"))
    assert caught.value.failure.code == "invalid_context"


@pytest.mark.parametrize(
    "limits",
    [
        PreviewLimits.model_construct(max_rows=0),
        PreviewLimits.model_construct(max_cells=10001),
        {"max_rows": 1},
    ],
)
def test_preview_rechecks_limits(limits: Any):
    with pytest.raises(BlockError) as caught:
        AddConstantBlock().preview(
            {}, input_values(1), BlockContext("run", "node"), limits
        )
    assert caught.value.failure.code == "invalid_preview_limits"


@pytest.mark.parametrize(
    "max_rows, max_cells, succeeds", [(3, 10, False), (5, 3, False), (5, 5, True)]
)
def test_preview_budget_is_shared_across_all_outputs(
    max_rows: int,
    max_cells: int,
    succeeds: bool,
):
    class MultipleOutputs(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "outputs": (
                    Port(name="first", data_schema=VALUE_SCHEMA),
                    Port(name="second", data_schema=VALUE_SCHEMA),
                )
            }
        )

        def _preview(
            self,
            config: AddConstantConfig,
            inputs: PortValues,
            context: BlockContext,
            limits: PreviewLimits,
        ) -> PortValues:
            return {"first": inputs["table"], "second": inputs["table"]}

    block = MultipleOutputs()
    limits = PreviewLimits(max_rows=max_rows, max_cells=max_cells)
    if succeeds:
        assert (
            len(
                block.preview(
                    {}, input_values(1, 2), BlockContext("run", "node"), limits
                )
            )
            == 2
        )
    else:
        with pytest.raises(BlockError) as caught:
            block.preview({}, input_values(1, 2), BlockContext("run", "node"), limits)
        assert caught.value.failure.code == "preview_limit"


def test_advertised_preview_requires_a_real_implementation():
    class MissingPreview(Block[AddConstantConfig]):
        config_model = AddConstantConfig
        descriptor = AddConstantBlock.descriptor

        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            return inputs

    with pytest.raises(BlockError) as caught:
        BlockRegistry().register(MissingPreview())
    assert caught.value.failure.code == "invalid_block"


def test_sink_preview_is_unsupported_without_execution():
    class Sink(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "block_type": "sink",
                "supports_preview": False,
                "preview_reason": "Sinks do not publish previews.",
            }
        )

        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            raise AssertionError("A preview must not execute a sink")

    with pytest.raises(BlockError) as caught:
        Sink().preview({}, input_values(1), BlockContext("run", "node"))
    assert caught.value.failure.code == "preview_unsupported"


def test_registered_configuration_model_cannot_drift():
    class DifferentConfig(AddConstantConfig):
        amount: int = 2

    block = AddConstantBlock()
    registry = BlockRegistry()
    registry.register(block)
    previous = registry.public_metadata()
    block.config_model = DifferentConfig
    with pytest.raises(BlockError) as caught:
        registry.resolve("synthetic.add_constant", "1.0.0")
    assert caught.value.failure.code == "invalid_block"
    assert registry.public_metadata() == previous


def test_unexpected_preview_failure_is_redacted_and_logged():
    class FailingPreview(AddConstantBlock):
        def _preview(
            self,
            config: AddConstantConfig,
            inputs: PortValues,
            context: BlockContext,
            limits: PreviewLimits,
        ) -> PortValues:
            raise RuntimeError("synthetic-secret and private-row")

    events: list[BlockEvent] = []
    with pytest.raises(BlockError) as caught:
        FailingPreview().preview(
            {}, input_values(1), BlockContext("run", "node", events.append)
        )
    assert caught.value.failure.code == "preview_failed"
    assert caught.value.failure.node_id == "node"
    assert [event.event for event in events] == ["failed"]
    assert events[0].error_code == "preview_failed"
    assert "synthetic-secret" not in caught.value.failure.model_dump_json()
