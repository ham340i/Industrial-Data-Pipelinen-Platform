"""durable run and block telemetry (#27)

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("error_code", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("error_reason", sa.String(length=512), nullable=True)
        )
        batch_op.create_check_constraint(
            op.f("ck_runs_duration"), "duration_ms IS NULL OR duration_ms >= 0"
        )

    op.create_table(
        "run_blocks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("block_id", sa.String(length=128), nullable=False),
        sa.Column("block_version", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("rows_in", sa.Integer(), nullable=True),
        sa.Column("rows_out", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_reason", sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "state IN ('queued','running','completed','failed','skipped')",
            name=op.f("ck_run_blocks_state"),
        ),
        sa.CheckConstraint("position >= 0", name=op.f("ck_run_blocks_position")),
        sa.CheckConstraint(
            "rows_in IS NULL OR rows_in >= 0", name=op.f("ck_run_blocks_rows_in")
        ),
        sa.CheckConstraint(
            "rows_out IS NULL OR rows_out >= 0", name=op.f("ck_run_blocks_rows_out")
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name=op.f("ck_run_blocks_duration"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_blocks_run_id_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_blocks")),
        sa.UniqueConstraint("run_id", "node_id", name=op.f("uq_run_blocks_run_id")),
    )
    with op.batch_alter_table("run_blocks", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_run_blocks_run_id"), ["run_id"], unique=False
        )

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.CheckConstraint("sequence >= 0", name=op.f("ck_run_events_sequence")),
        sa.CheckConstraint(
            "level IN ('info','warning','error')", name=op.f("ck_run_events_level")
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_events_run_id_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_events")),
        sa.UniqueConstraint("run_id", "sequence", name=op.f("uq_run_events_run_id")),
    )
    with op.batch_alter_table("run_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_run_events_run_id"), ["run_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("run_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_run_events_run_id"))
    op.drop_table("run_events")
    with op.batch_alter_table("run_blocks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_run_blocks_run_id"))
    op.drop_table("run_blocks")
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_runs_duration"), type_="check")
        batch_op.drop_column("error_reason")
        batch_op.drop_column("error_code")
        batch_op.drop_column("duration_ms")
