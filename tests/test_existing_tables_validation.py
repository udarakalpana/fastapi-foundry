from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry.cli import app
from fastapi_foundry.generators.migration import (
    MIGRATIONS_DIR,
    MigrationKind,
    create_migration,
    existing_tables,
)
from fastapi_foundry.generators.project import create_project


def _write_migration(project_root: Path, filename: str, table: str) -> None:
    """Write a migration as if its TABLE line had been edited by hand."""
    directory = project_root / MIGRATIONS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(f'TABLE = "{table}"\n')


# --- existing_tables ------------------------------------------------------


@pytest.mark.parametrize(
    "invalid_table",
    ["my posts", "my-posts", "1posts", "../evil", "posts;drop", "", "p" * 65],
)
def test_invalid_hand_edited_table_names_are_skipped(tmp_path: Path, invalid_table: str) -> None:
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path)
    _write_migration(tmp_path, "20260101000000_create_posts_table.py", invalid_table)

    assert existing_tables(tmp_path) == ["users"]


def test_hand_edited_table_names_are_normalized(tmp_path: Path) -> None:
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path)
    _write_migration(tmp_path, "20260101000000_update_users_table.py", "  Users ")
    _write_migration(tmp_path, "20260101000001_create_posts_table.py", "POSTS")

    assert existing_tables(tmp_path) == ["posts", "users"]


# --- CLI ------------------------------------------------------------------


def test_cli_menu_does_not_offer_invalid_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    _write_migration(project_root, "20260101000000_create_posts_table.py", "my posts")
    monkeypatch.chdir(project_root)

    # Option 1 is "users", the only valid table left in the menu.
    result = CliRunner().invoke(app, ["migration"], input="1\n1\n")

    assert result.exit_code == 0, result.output
    assert "my posts" not in result.output
    assert list((project_root / MIGRATIONS_DIR).glob("*_update_users_table.py"))


def test_cli_with_only_invalid_tables_reports_none_without_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    for migration_file in (project_root / MIGRATIONS_DIR).glob("*.py"):
        migration_file.unlink()
    _write_migration(project_root, "20260101000000_create_posts_table.py", "my posts")
    monkeypatch.chdir(project_root)

    result = CliRunner().invoke(app, ["migration"], input="1\n1\n")

    assert result.exit_code == 1
    assert "No existing tables" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
