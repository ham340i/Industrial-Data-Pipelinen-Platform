"""Reproducible synthetic SDK demonstration for #16, #18 and #20.

Run from the repository root: python -m scripts.demo_file_blocks
This fixed workflow is not the future #22 execution engine or a file upload API.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.blocks.catalog import registry
from app.blocks.context import BlockContext
from app.blocks.contracts import Table


def demo() -> dict[str, object]:
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/blocks"
    expected = json.loads((fixtures / "file_golden.json").read_text())["filtered"]
    with TemporaryDirectory(prefix="lps-file-demo-") as directory:
        root = Path(directory)
        (root / "input.csv").write_bytes((fixtures / "file_pipeline.csv").read_bytes())
        context = BlockContext("synthetic-demo", "source", workspace_root=root)
        table = registry.resolve("source.csv", "1.0.0").run(
            {"resource_ref": "input.csv"}, {}, context
        )["table"][0]
        for block_id, config in (
            ("transform.select", {"columns": ["sensor", "reading"]}),
            ("transform.cast", {"column": "reading", "dtype": "number"}),
            ("transform.rename", {"columns": ["reading"], "names": ["temperature"]}),
            (
                "transform.filter",
                {"column": "temperature", "operator": "gt", "value_text": "0"},
            ),
        ):
            table = registry.resolve(block_id, "1.0.0").run(
                config, {"table": (table,)}, context
            )["table"][0]
        assert isinstance(table, Table)
        assert list(table.rows) == expected
        artifacts = []
        for extension in ("csv", "parquet"):
            artifacts.append(
                registry.resolve("sink." + extension, "1.0.0")
                .run(
                    {"resource_ref": "result." + extension},
                    {"table": (table,)},
                    context,
                )["artifact"][0]
                .model_dump(mode="json")
            )
        return {"verified": True, "rows": expected, "artifacts": artifacts}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True))
