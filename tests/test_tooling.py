from __future__ import annotations

from pathlib import Path


def test_tool_configs_present() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproj = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.ruff]" in pyproj
    assert "[tool.mypy]" in pyproj


def test_pre_commit_hooks_present() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "ruff-pre-commit" in cfg
    assert "mirrors-mypy" in cfg
