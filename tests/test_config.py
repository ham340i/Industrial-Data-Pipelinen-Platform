# AI contribution: 50% or more AI-generated
"""Workspace configuration shared by SQL sources and artifact storage."""

from pathlib import Path

from app.config import Settings


def test_workspace_root_default(monkeypatch):
    monkeypatch.delenv("LPS_WORKSPACE_ROOT", raising=False)

    assert Settings().workspace_root == Path("local-data/workspace")


def test_workspace_root_from_environment(monkeypatch, tmp_path):
    root = tmp_path / "custom-workspace"
    monkeypatch.setenv("LPS_WORKSPACE_ROOT", str(root))

    assert Settings().workspace_root == root
