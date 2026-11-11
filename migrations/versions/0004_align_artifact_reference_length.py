"""align artifact reference length

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("output_endpoints", schema=None) as batch_op:
        batch_op.alter_column(
            "artifact_ref",
            existing_type=sa.String(length=128),
            type_=sa.String(length=256),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("output_endpoints", schema=None) as batch_op:
        batch_op.alter_column(
            "artifact_ref",
            existing_type=sa.String(length=256),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
