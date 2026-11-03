"""govern parquet artifacts

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill legacy output rows with an explicit unknown schema, then require
    # every newly registered artifact to provide its real schema.
    with op.batch_alter_table("output_endpoints", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "schema_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )

    with op.batch_alter_table("output_endpoints", schema=None) as batch_op:
        batch_op.alter_column("schema_json", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("output_endpoints", schema=None) as batch_op:
        batch_op.drop_column("schema_json")
