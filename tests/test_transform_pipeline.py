"""Integration coverage for the issue #24 transform pipeline."""

from pathlib import Path

from app.blocks.catalog import registry
from app.blocks.context import BlockContext
from app.blocks.contracts import Column, DataSchema, Table


def left_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="region", dtype="string"),
            )
        ),
        rows=(
            {"customer_id": 1, "region": "east"},
            {"customer_id": 1, "region": "east"},
            {"customer_id": 2, "region": "west"},
        ),
    )


def right_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="amount", dtype="number"),
            )
        ),
        rows=(
            {"customer_id": 1, "amount": 10.0},
            {"customer_id": 2, "amount": 5.0},
        ),
    )


def test_join_aggregate_sort_pipeline(tmp_path: Path):
    context = BlockContext(
        run_id="issue-24-integration",
        node_id="join",
        workspace_root=tmp_path,
    )

    joined = registry.resolve("transform.join", "1.0.0").run(
        {
            "left_on": ["customer_id"],
            "right_on": ["customer_id"],
            "how": "inner",
            "cardinality": "many_to_many",
        },
        {
            "left": (left_table(),),
            "right": (right_table(),),
        },
        context,
    )["table"][0]

    assert isinstance(joined, Table)
    assert joined.rows == (
        {
            "customer_id": 1,
            "region": "east",
            "amount": 10.0,
        },
        {
            "customer_id": 1,
            "region": "east",
            "amount": 10.0,
        },
        {
            "customer_id": 2,
            "region": "west",
            "amount": 5.0,
        },
    )

    aggregate_context = BlockContext(
        run_id="issue-24-integration",
        node_id="aggregate",
        workspace_root=tmp_path,
    )

    aggregated = registry.resolve("transform.aggregate", "1.0.0").run(
        {
            "group_by": ["region"],
            "operations": [
                {
                    "column": "amount",
                    "function": "sum",
                    "output_name": "amount_sum",
                },
                {
                    "column": "amount",
                    "function": "count",
                    "output_name": "amount_count",
                },
            ],
        },
        {"table": (joined,)},
        aggregate_context,
    )["table"][0]

    assert isinstance(aggregated, Table)
    assert aggregated.rows == (
        {
            "region": "east",
            "amount_sum": 20.0,
            "amount_count": 2,
        },
        {
            "region": "west",
            "amount_sum": 5.0,
            "amount_count": 1,
        },
    )

    sort_context = BlockContext(
        run_id="issue-24-integration",
        node_id="sort",
        workspace_root=tmp_path,
    )

    sorted_table = registry.resolve("transform.sort", "1.0.0").run(
        {
            "columns": [
                {
                    "column": "amount_sum",
                    "descending": True,
                    "nulls_last": True,
                },
            ],
        },
        {"table": (aggregated,)},
        sort_context,
    )["table"][0]

    assert isinstance(sorted_table, Table)
    assert sorted_table.rows == (
        {
            "region": "east",
            "amount_sum": 20.0,
            "amount_count": 2,
        },
        {
            "region": "west",
            "amount_sum": 5.0,
            "amount_count": 1,
        },
    )

    assert sorted_table.data_schema == DataSchema(
        columns=(
            Column(name="region", dtype="string"),
            Column(name="amount_sum", dtype="number"),
            Column(name="amount_count", dtype="integer"),
        )
    )
