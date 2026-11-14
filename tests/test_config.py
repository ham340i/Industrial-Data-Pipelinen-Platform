# AI contribution: 50% or more AI-generated
"""Workspace configuration shared by SQL sources and artifact storage."""

import json

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_workspace_root_default(monkeypatch):
    monkeypatch.delenv("LPS_WORKSPACE_ROOT", raising=False)

    assert Settings().workspace_root is None


def test_workspace_root_from_environment(monkeypatch, tmp_path):
    root = tmp_path / "custom-workspace"
    monkeypatch.setenv("LPS_WORKSPACE_ROOT", str(root))

    assert Settings().workspace_root == root


def test_allowed_workspace_roots_from_environment(monkeypatch, tmp_path):
    roots = [tmp_path / "first", tmp_path / "second"]
    monkeypatch.setenv("LPS_ALLOWED_WORKSPACE_ROOTS", json.dumps(list(map(str, roots))))
    assert Settings().allowed_workspace_roots == roots


def test_allowed_workspace_roots_rejects_non_list(monkeypatch):
    monkeypatch.setenv("LPS_ALLOWED_WORKSPACE_ROOTS", '{"path":"/tmp"}')
    with pytest.raises(ValidationError):
        Settings()
