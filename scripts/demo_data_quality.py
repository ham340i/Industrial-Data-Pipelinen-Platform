"""Synthetic, local-only quality gate demonstration (#25); no real data."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.blocks.catalog import registry  # noqa: E402
from app.execution import Executor  # noqa: E402
from app.pipelines.models import Edge, Node, PipelineDefinition, PortReference  # noqa: E402


def graph(required):
    return PipelineDefinition(
        nodes=(
            Node(id="source", block_id="source.csv", block_version="1.0.0", config={
                "resource_ref": "input.csv", "columns": ["value"],
                "types": ["integer"], "nullable": [True],
            }),
            Node(id="check", block_id="quality.null_check", block_version="1.0.0",
                 config={"required": required}),
            Node(id="sink", block_id="sink.csv", block_version="1.0.0",
                 config={"resource_ref": "output.csv"}),
        ),
        edges=tuple(Edge(id=str(i), source=PortReference(node_id=a, port="table"),
                         target=PortReference(node_id=b, port="table"))
                    for i, (a, b) in enumerate((("source", "check"), ("check", "sink")))),
    )


def main():
    # Hand-worked: one null violates max_nulls=0; optional mode permits the same row.
    for required, expected in ((True, "failed"), (False, "completed")):
        with TemporaryDirectory(prefix="quality-demo-") as folder:
            root = Path(folder)
            (root / "input.csv").write_text("value\nNULL\n")
            result = Executor(registry).execute(graph(required), workspace_root=root)
            published = (root / "output.csv").exists()
            assert result.state == expected and published is not required
            print(f"required={required}: run={result.state}, "
                  f"sink={result.node_states['sink']}, published={published}")
            for event in result.block_events:
                for diagnostic in event.diagnostics:
                    print(diagnostic.model_dump_json())


if __name__ == "__main__":
    main()
