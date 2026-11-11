"""SDK reference retained for authors, contract tests and saved pipelines.

Hidden from the builder library. This deliberately small transform accepts only
one non-nullable integer column named ``value``. Its preview demonstrates the SDK
hook on supplied input; it does not implement bounded file or upstream reading.
"""

from typing import cast

from pydantic import Field

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockDescriptor,
    BlockConfig,
    Column,
    DataSchema,
    Port,
    PortValues,
    PreviewLimits,
    Table,
)

VALUE_SCHEMA = DataSchema(columns=(Column(name="value", dtype="integer"),))


class AddConstantConfig(BlockConfig):
    amount: int = Field(default=1, ge=-1000, le=1000)


class AddConstantBlock(Block[AddConstantConfig]):
    config_model: type[AddConstantConfig] = AddConstantConfig
    descriptor = BlockDescriptor(
        block_id="synthetic.add_constant",
        version="1.0.0",
        block_type="transform",
        name="Synthetic Add Constant",
        category="synthetic",
        library_visible=False,
        inputs=(Port(name="table", data_schema=VALUE_SCHEMA),),
        outputs=(Port(name="table", data_schema=VALUE_SCHEMA),),
        supports_preview=True,
        preview_reason=None,
    )

    def _execute(
        self,
        config: AddConstantConfig,
        inputs: PortValues,
        context: BlockContext,
    ) -> PortValues:
        table = inputs["table"][0]
        assert isinstance(table, Table)
        return {
            "table": (
                Table(
                    data_schema=VALUE_SCHEMA,
                    rows=tuple(
                        {"value": cast(int, row["value"]) + config.amount}
                        for row in table.rows
                    ),
                ),
            )
        }

    def _preview(
        self,
        config: AddConstantConfig,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        table = inputs["table"][0]
        assert isinstance(table, Table)
        count = min(limits.max_rows, limits.max_cells)
        sample = Table(data_schema=table.data_schema, rows=table.rows[:count])
        return self._execute(config, {"table": (sample,)}, context)
