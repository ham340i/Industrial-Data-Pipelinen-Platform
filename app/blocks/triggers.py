# AI contribution: below 50% AI-generated
"""Manual and bounded Timer trigger contracts (#29).

Triggers start a run; they never emit tabular data. ``BlockDescriptor``
already enforces that a ``trigger`` block's outputs are all ``kind="control"``
(see ``app.blocks.contracts``), so these blocks only ever hand the executor a
``ControlSignal``, never a ``Table``.
"""

from pydantic import Field

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    ControlSignal,
    Port,
    PortValues,
)

SIGNAL = (Port(name="signal", kind="control"),)


class ManualTrigger(Block[BlockConfig]):
    """Starts a run only when an operator calls the execute API directly."""

    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="trigger.manual",
        version="1.0.0",
        block_type="trigger",
        name="Manual Trigger",
        category="trigger",
        outputs=SIGNAL,
    )

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"signal": (ControlSignal(),)}


class TimerTriggerConfig(BlockConfig):
    interval_seconds: int = Field(
        ge=1,
        le=86400,
        description="Seconds between runs while the local service is running "
        "(1 second to 24 hours). No cron or distributed scheduling.",
    )


class TimerTrigger(Block[TimerTriggerConfig]):
    """Starts a run on a bounded, single-process interval.

    The interval is declarative config read by ``app.runs.scheduler`` when a
    timer is started for the owning pipeline; this block's own execution
    contributes nothing but the control signal that starts the run, exactly
    like ``ManualTrigger``.
    """

    config_model = TimerTriggerConfig
    descriptor = BlockDescriptor(
        block_id="trigger.timer",
        version="1.0.0",
        block_type="trigger",
        name="Timer Trigger",
        category="trigger",
        outputs=SIGNAL,
    )

    def _execute(
        self, config: TimerTriggerConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"signal": (ControlSignal(),)}
