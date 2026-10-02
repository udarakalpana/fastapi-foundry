from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry.cli import app
from fastapi_foundry.generators.migration import (
    MIGRATIONS_DIR,
    NotAProjectError,
    ensure_project_root,
)
from fastapi_foundry.generators.project import create_project


def _make_project_markers(root: Path) -> None:
    (root / "app").mkdir()
    (root / "app" / "routes.py").write_text("")
    (root / "pyproject.toml").write_text("")


# --- ensure_project_root --------------------------------------------------


def test_generated_project_is_accepted(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    ensure_project_root(project_root)


def test_directory_with_project_markers_is_accepted(tmp_path: Path) -> None:
    _make_project_markers(tmp_path)

    ensure_project_root(tmp_path)


def test_empty_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(NotAProjectError):
        ensure_project_root(tmp_path)


@pytest.mark.parametrize("missing", ["pyproject.toml", "app/routes.py"])
def test_directory_missing_a_marker_is_rejected(tmp_path: Path, missing: str) -> None:
    _make_project_markers(tmp_path)
    (tmp_path / missing).unlink()

    with pytest.raises(NotAProjectError):
        ensure_project_root(tmp_path)


def test_project_subdirectory_is_rejected(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    with pytest.raises(NotAProjectError):
        ensure_project_root(project_root / "app")


# --- CLI ------------------------------------------------------------------


def test_cli_migration_outside_a_project_fails_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["migration"], input="2\nusers\n")

    assert result.exit_code == 1
    assert "project's root" in result.output
    # Fails before asking anything, and leaves no stray directories behind.
    assert "Is this migration" not in result.output
    assert not (tmp_path / "app").exists()


def test_cli_migration_from_project_subdirectory_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    monkeypatch.chdir(project_root / "app")

    result = CliRunner().invoke(app, ["migration"], input="2\nposts\n")

    assert result.exit_code == 1
    assert not (project_root / "app" / "app").exists()


def test_cli_migration_inside_a_generated_project_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    monkeypatch.chdir(project_root)

    result = CliRunner().invoke(app, ["migration"], input="2\nposts\n")

    assert result.exit_code == 0, result.output
    assert list((project_root / MIGRATIONS_DIR).glob("*_create_posts_table.py"))
