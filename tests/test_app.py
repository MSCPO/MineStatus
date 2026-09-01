"""Smoke test: the FastAPI app module must import cleanly."""

import tomllib
from pathlib import Path


def test_app_imports_and_version_matches_pyproject():
    """The app can be imported and reports the version from pyproject.toml."""
    import main  # noqa: F401

    assert main.app.title == "MineStatus API"

    root = Path(__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        expected_version = tomllib.load(f)["project"]["version"]
    assert main.app.version == expected_version