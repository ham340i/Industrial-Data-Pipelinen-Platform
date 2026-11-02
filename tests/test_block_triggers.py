# AI contribution: 50% or more AI-generated
"""Manual and Timer trigger block contracts (#29)."""

import pytest
from pydantic import ValidationError

from app.blocks.catalog import registry
from app.blocks.context import BlockContext
from app.blocks.contracts import BlockConfig, ControlSignal
from app.blocks.triggers import ManualTrigger, TimerTrigger, TimerTriggerConfig


def context() -> BlockContext:
    return BlockContext("run", "n0")


def test_manual_trigger_emits_only_a_control_signal():
    block = ManualTrigger()
    assert block.descriptor.block_type == "trigger"
    assert [port.kind for port in block.descriptor.outputs] == ["control"]
    assert block.descriptor.inputs == ()

    result = block._execute(BlockConfig(), {}, context())
    assert result == {"signal": (ControlSignal(),)}


def test_timer_trigger_emits_only_a_control_signal():
    block = TimerTrigger()
    assert block.descriptor.block_type == "trigger"
    assert [port.kind for port in block.descriptor.outputs] == ["control"]
    assert block.descriptor.inputs == ()

    config = TimerTriggerConfig(interval_seconds=30)
    result = block._execute(config, {}, context())
    assert result == {"signal": (ControlSignal(),)}


@pytest.mark.parametrize("interval", [1, 86400])
def test_timer_interval_bounds_are_accepted(interval: int):
    assert TimerTriggerConfig(interval_seconds=interval).interval_seconds == interval


@pytest.mark.parametrize("interval", [0, -1, 86401])
def test_timer_interval_out_of_bounds_is_rejected(interval: int):
    with pytest.raises(ValidationError):
        TimerTriggerConfig(interval_seconds=interval)


def test_timer_interval_is_required():
    with pytest.raises(ValidationError):
        TimerTriggerConfig.model_validate({})


def test_both_triggers_are_registered_as_trigger_type():
    manual = registry.resolve("trigger.manual", "1.0.0")
    timer = registry.resolve("trigger.timer", "1.0.0")
    assert manual.descriptor.block_type == timer.descriptor.block_type == "trigger"
    assert manual.descriptor.category == timer.descriptor.category == "trigger"
