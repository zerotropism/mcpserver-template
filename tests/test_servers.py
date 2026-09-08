"""Smoke tests: both server variants load and expose a FastMCP app."""

import importlib.util
import sys
from pathlib import Path

import pytest
from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ["list-based-memory", "sqlite-based-memory"]


def _load(variant: str, module: str):
    """Load a module by path, avoiding sys.modules name collisions."""
    path = ROOT / variant / f"{module}.py"
    name = f"{variant.replace('-', '_')}_{module}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    sys.path.insert(0, str(ROOT / variant))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(ROOT / variant))
    return mod


@pytest.mark.parametrize("variant", VARIANTS)
def test_server_exposes_fastmcp_app(variant, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "tasks.db"))
    mod = _load(variant, "server")
    assert any(isinstance(v, FastMCP) for v in vars(mod).values())


@pytest.mark.parametrize("variant", VARIANTS)
def test_client_imports(variant, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "tasks.db"))
    _load(variant, "client")
    _load(variant, "ollama_client")
