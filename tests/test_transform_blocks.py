def join_left_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="region", dtype="string"),
                Column(name="customer_name", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "region": "east",
                "customer_name": "Alpha",
            },
            {
                "customer_id": 1,
                "region": "east",
                "customer_name": "Alpha",
            },
            {
                "customer_id": 2,
                "region": "west",
                "customer_name": "Beta",
            },
            {
                "customer_id": 3,
                "region": "north",
                "customer_name": "Gamma",
            },
        ),
    )


def join_right_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="amount", dtype="number", nullable=True),
                Column(name="segment", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "amount": 10.0,
                "segment": "industrial",
            },
            {
                "customer_id": 1,
                "amount": 12.5,
                "segment": "industrial",
            },
            {
                "customer_id": 2,
                "amount": 5.0,
                "segment": "commercial",
            },
            {
                "customer_id": 4,
                "amount": None,
                "segment": "unknown",
            },
        ),
    )


def run_join(
    tmp_path: Path,
    config: dict[str, Any],
    left: Table | None = None,
    right: Table | None = None,
) -> Table:
    block = Join()

    outputs = block.run(
        config,
        {
            "left": (join_left_table() if left is None else left,),
            "right": (join_right_table() if right is None else right,),
        },
        BlockContext(
            run_id="join-test",
            node_id="join",
            workspace_root=tmp_path,
        ),
    )

    value = outputs["table"][0]
    assert isinstance(value, Table)
    return value


def run_aggregate(
    tmp_path: Path,
    config: dict[str, Any],
    table: Table,
) -> Table:
    return run(Aggregate(), tmp_path, config, table)


def run_sort(
    tmp_path: Path,
    config: dict[str, Any],
    table: Table,
) -> Table:
    return run(Sort(), tmp_path, config, table)


def test_join_inner_multiples_duplicate_keys(tmp_path: Path):
    actual = run_join(
        tmp_path,
        {
            "left_on": ["customer_id"],
            "right_on": ["customer_id"],
            "how": "inner",
            "cardinality": "many_to_many",
        },
    )

    assert actual.rows == (
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 10.0,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 12.5,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 10.0,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 12.5,
            "segment": "industrial",
        },
        {
            "customer_id": 2,
            "region": "west",
            "customer_name": "Beta",
            "amount": 5.0,
            "segment": "commercial",
        },
    )

    assert actual.data_schema.columns == (
        Column(name="customer_id", dtype="integer"),
        Column(name="region", dtype="string"),
        Column(name="customer_name", dtype="string"),
        Column(name="amount", dtype="number", nullable=True),
        Column(name="segment", dtype="string"),
    )


def test_join_left_preserves_unmatched_left_rows(tmp_path: Path):
    actual = run_join(
        tmp_path,
        {
            "left_on": ["customer_id"],
            "right_on": ["customer_id"],
            "how": "left",
            "cardinality": "many_to_many",
        },
    )

    assert actual.rows[-1] == {
        "customer_id": 3,
        "region": "north",
        "customer_name": "Gamma",
        "amount": None,
        "segment": None,
    }

    amount_column = next(
        column for column in actual.data_schema.columns if column.name == "amount"
    )
    segment_column = next(
        column for column in actual.data_schema.columns if column.name == "segment"
    )

    assert amount_column.nullable
    assert segment_column.nullable


def test_join_rejects_missing_key(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["missing"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
        )

    assert error.value.failure.code == "missing_column"


def test_join_rejects_mismatched_key_lengths(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id", "region"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
        )

    assert error.value.failure.code == "invalid_config"


def test_join_rejects_invalid_one_to_one_cardinality(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "one_to_one",
            },
        )

    assert error.value.failure.code == "invalid_cardinality"


def test_join_rejects_duplicate_output_columns(tmp_path: Path):
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="region", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "region": "duplicate",
            },
        ),
    )

    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
            right=right,
        )

    assert error.value.failure.code == "duplicate_column"


def test_aggregate_grouped_sum_and_count(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="region", dtype="string"),
                Column(name="amount", dtype="number", nullable=True),
            )
        ),
        rows=(
            {"region": "east", "amount": 10.0},
            {"region": "east", "amount": 12.5},
            {"region": "west", "amount": 5.0},
            {"region": "west", "amount": None},
        ),
    )

    actual = run_aggregate(
        tmp_path,
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
        source,
    )

    assert actual.rows == (
        {
            "region": "east",
            "amount_sum": 22.5,
            "amount_count": 2,
        },
        {
            "region": "west",
            "amount_sum": 5.0,
            "amount_count": 1,
        },
    )

    assert [column.name for column in actual.data_schema.columns] == [
        "region",
        "amount_sum",
        "amount_count",
    ]


def test_aggregate_mean_ignores_null_values(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="group", dtype="string"),
                Column(name="value", dtype="number", nullable=True),
            )
        ),
        rows=(
            {"group": "a", "value": 2.0},
            {"group": "a", "value": None},
            {"group": "a", "value": 4.0},
        ),
    )

    actual = run_aggregate(
        tmp_path,
        {
            "group_by": ["group"],
            "operations": [
                {
                    "column": "value",
                    "function": "mean",
                    "output_name": "value_mean",
                },
            ],
        },
        source,
    )

    assert actual.rows == (
        {
            "group": "a",
            "value_mean": 3.0,
        },
    )


def test_aggregate_empty_input_preserves_output_schema(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="group", dtype="string"),
                Column(name="value", dtype="number", nullable=True),
            )
        ),
        rows=(),
    )

    actual = run_aggregate(
        tmp_path,
        {
            "group_by": ["group"],
            "operations": [
                {
                    "column": "value",
                    "function": "sum",
                    "output_name": "value_sum",
                },
                {
                    "column": "value",
                    "function": "count",
                    "output_name": "value_count",
                },
            ],
        },
        source,
    )

    assert actual.rows == ()
    assert [column.name for column in actual.data_schema.columns] == [
        "group",
        "value_sum",
        "value_count",
    ]


def test_aggregate_rejects_missing_column(tmp_path: Path):
    source = join_left_table()

    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["region"],
                "operations": [
                    {
                        "column": "missing",
                        "function": "sum",
                        "output_name": "total",
                    },
                ],
            },
            source,
        )

    assert error.value.failure.code == "missing_column"


def test_aggregate_rejects_duplicate_output_names(tmp_path: Path):
    source = join_left_table()

    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["region"],
                "operations": [
                    {
                        "column": "customer_id",
                        "function": "count",
                        "output_name": "value",
                    },
                    {
                        "column": "customer_id",
                        "function": "sum",
                        "output_name": "value",
                    },
                ],
            },
            source,
        )

    assert error.value.failure.code == "invalid_config"


def test_sort_is_stable_and_places_nulls_last(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="priority", dtype="integer", nullable=True),
                Column(name="sequence", dtype="integer"),
                Column(name="label", dtype="string"),
            )
        ),
        rows=(
            {"priority": None, "sequence": 1, "label": "null-first"},
            {"priority": 1, "sequence": 2, "label": "first"},
            {"priority": 1, "sequence": 3, "label": "second"},
            {"priority": None, "sequence": 4, "label": "null-second"},
        ),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "priority",
                    "descending": False,
                    "nulls_last": True,
                },
            ],
        },
        source,
    )

    assert actual.rows == (
        {"priority": 1, "sequence": 2, "label": "first"},
        {"priority": 1, "sequence": 3, "label": "second"},
        {"priority": None, "sequence": 1, "label": "null-first"},
        {"priority": None, "sequence": 4, "label": "null-second"},
    )

    assert actual.data_schema == source.data_schema


def test_sort_supports_descending_nulls_first(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="value", dtype="integer", nullable=True),
            )
        ),
        rows=(
            {"value": 1},
            {"value": None},
            {"value": 3},
            {"value": 2},
        ),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "value",
                    "descending": True,
                    "nulls_last": False,
                },
            ],
        },
        source,
    )

    assert actual.rows == (
        {"value": None},
        {"value": 3},
        {"value": 2},
        {"value": 1},
    )


def test_sort_empty_input_preserves_schema(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="value", dtype="integer", nullable=True),
                Column(name="label", dtype="string"),
            )
        ),
        rows=(),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "value",
                    "descending": False,
                    "nulls_last": True,
                },
            ],
        },
        source,
    )

    assert actual.rows == ()
    assert actual.data_schema == source.data_schema


def test_sort_rejects_missing_column(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_sort(
            tmp_path,
            {
                "columns": [
                    {
                        "column": "missing",
                        "descending": False,
                        "nulls_last": True,
                    },
                ],
            },
            join_left_table(),
        )

    assert error.value.failure.code == "missing_column"