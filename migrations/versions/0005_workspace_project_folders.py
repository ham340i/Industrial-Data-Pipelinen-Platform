"""Associate projects with workspaces and retain readable folder mappings.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects", sa.Column("workspace_root", sa.String(4096), nullable=True)
    )
    op.add_column(
        "projects", sa.Column("directory_name", sa.String(128), nullable=True)
    )
    op.create_index("ix_projects_workspace_root", "projects", ["workspace_root"])
    op.add_column(
        "pipelines", sa.Column("directory_name", sa.String(128), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("pipelines", "directory_name")
    op.drop_index("ix_projects_workspace_root", table_name="projects")
    op.drop_column("projects", "directory_name")
    op.drop_column("projects", "workspace_root")
