"""SQLAlchemy 2 metadata entities with retained, versioned pipeline history."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    MetaData,
    String,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.metadata.portable import PortableJSON, portable_definition


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    """SQLite stores naive timestamps; all values in this schema are UTC."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 128", name="name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    pipelines: Mapped[list[Pipeline]] = relationship(back_populates="project")
    bindings: Mapped[list[WorkspaceBinding]] = relationship(back_populates="project")


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("project_id", "name"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 128", name="name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    project: Mapped[Project] = relationship(back_populates="pipelines")
    revisions: Mapped[list[PipelineRevision]] = relationship(back_populates="pipeline")


class PipelineRevision(Base):
    __tablename__ = "pipeline_revisions"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "revision"),
        CheckConstraint("revision > 0", name="revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id", ondelete="RESTRICT"), index=True
    )
    revision: Mapped[int]
    _definition: Mapped[dict[str, Any]] = mapped_column("definition", PortableJSON())
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    pipeline: Mapped[Pipeline] = relationship(back_populates="revisions")
    runs: Mapped[list[Run]] = relationship(back_populates="pipeline_revision")

    @property
    def definition(self) -> dict[str, Any]:
        """Export only the authoritative portable JSON, as a detached copy."""
        return copy.deepcopy(self._definition)

    @definition.setter
    def definition(self, value: dict[str, Any]) -> None:
        if inspect(self).persistent:
            raise ValueError("Persisted revisions are immutable; create a new revision")
        self._definition = portable_definition(value)


@event.listens_for(PipelineRevision, "before_update")
def reject_revision_update(
    mapper: object, connection: object, target: PipelineRevision
) -> None:
    state = inspect(target)
    if any(
        state.attrs[column.key].history.has_changes()
        for column in state.mapper.column_attrs
    ):
        raise ValueError("Persisted revisions are immutable; create a new revision")


class WorkspaceBinding(Base):
    """Private runtime resolution data; never included in a portable definition."""

    __tablename__ = "workspace_bindings"
    __table_args__ = (
        UniqueConstraint("project_id", "resource_id"),
        CheckConstraint("length(trim(resource_id)) > 0", name="resource_id"),
        CheckConstraint(
            "local_path IS NOT NULL OR secret_reference IS NOT NULL", name="target"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    resource_id: Mapped[str] = mapped_column(String(128))
    local_path: Mapped[str | None]
    secret_reference: Mapped[str | None]
    project: Mapped[Project] = relationship(back_populates="bindings")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','succeeded','failed','cancelled')",
            name="state",
        ),
        CheckConstraint("row_count IS NULL OR row_count >= 0", name="row_count"),
        CheckConstraint(
            "ended_at IS NULL OR (started_at IS NOT NULL AND ended_at >= started_at)",
            name="times",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pipeline_revision_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_revisions.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[str] = mapped_column(String(16), default="queued")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
    row_count: Mapped[int | None]
    pipeline_revision: Mapped[PipelineRevision] = relationship(back_populates="runs")
    outputs: Mapped[list[OutputEndpoint]] = relationship(back_populates="run")


class BlockRegistryEntry(Base):
    __tablename__ = "block_registry"
    __table_args__ = (
        CheckConstraint(
            "length(trim(block_id)) > 0 AND length(trim(version)) > 0", name="identity"
        ),
    )

    block_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), index=True)
    public_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)


class OutputEndpoint(Base):
    __tablename__ = "output_endpoints"
    __table_args__ = (
        UniqueConstraint("run_id", "node_id", "name"),
        CheckConstraint("format IN ('csv','parquet')", name="format"),
        CheckConstraint("row_count IS NULL OR row_count >= 0", name="row_count"),
        CheckConstraint("length(trim(artifact_ref)) > 0", name="artifact_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="RESTRICT"), index=True
    )
    node_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    format: Mapped[str] = mapped_column(String(16))
    artifact_ref: Mapped[str] = mapped_column(String(128))
    row_count: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    run: Mapped[Run] = relationship(back_populates="outputs")
