from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry.cli import app
from fastapi_foundry.generators.migration import (
    MIGRATIONS_DIR,
    InvalidTableNameError,
    MigrationKind,
    create_migration,
    existing_tables,
    normalize_table_name,
)

FIXED_NOW = datetime(2026, 9, 16, 14, 30, 22, tzinfo=timezone.utc)


# --- normalize_table_name -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("users", "users"), ("Users", "users"), ("  users  ", "users"), ("user_roles", "user_roles")],
)
def test_table_names_are_normalized(raw: str, expected: str) -> None:
    assert normalize_table_name(raw) == expected


@pytest.mark.parametrize(
    "invalid_name",
    ["", "   ", "1users", "user-roles", "user roles", "../evil", "a/b", "users;drop", "user.roles", "u" * 65],
)
def test_invalid_table_names_are_rejected(invalid_name: str) -> None:
    with pytest.raises(InvalidTableNameError):
        normalize_table_name(invalid_name)


# --- create_migration -----------------------------------------------------


def test_create_migration_creates_directory_and_file(tmp_path: Path) -> None:
    migration_path = create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    migrations_dir = tmp_path / MIGRATIONS_DIR
    assert migrations_dir.is_dir()
    assert migration_path.parent == migrations_dir
    assert migration_path.is_file()


def test_new_table_migration_filename(tmp_path: Path) -> None:
    migration_path = create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    assert migration_path.name == "20260916143022_create_users_table.py"


def test_existing_table_migration_filename(tmp_path: Path) -> None:
    migration_path = create_migration("users", MigrationKind.EXISTING_TABLE, tmp_path, now=FIXED_NOW)

    assert migration_path.name == "20260916143022_update_users_table.py"


def test_migration_file_records_table_name_and_compiles(tmp_path: Path) -> None:
    migration_path = create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    source = migration_path.read_text()
    assert 'TABLE = "users"' in source
    compile(source, str(migration_path), "exec")


def test_create_migration_reuses_an_existing_migrations_directory(tmp_path: Path) -> None:
    first = create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    second = create_migration("posts", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    assert first.parent == second.parent
    assert first.is_file() and second.is_file()


def test_migrations_in_the_same_second_do_not_overwrite(tmp_path: Path) -> None:
    first = create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    second = create_migration("users", MigrationKind.EXISTING_TABLE, tmp_path, now=FIXED_NOW)
    third = create_migration("users", MigrationKind.EXISTING_TABLE, tmp_path, now=FIXED_NOW)

    assert len({first, second, third}) == 3
    assert third.is_file()


def test_create_migration_rejects_invalid_table_name(tmp_path: Path) -> None:
    with pytest.raises(InvalidTableNameError):
        create_migration("../evil", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    assert not (tmp_path / MIGRATIONS_DIR).exists()


# --- existing_tables ------------------------------------------------------


def test_existing_tables_is_empty_without_a_migrations_directory(tmp_path: Path) -> None:
    assert existing_tables(tmp_path) == []


def test_existing_tables_lists_tables_from_previous_migrations(tmp_path: Path) -> None:
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    create_migration("posts", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    assert existing_tables(tmp_path) == ["posts", "users"]


def test_existing_tables_deduplicates_repeated_tables(tmp_path: Path) -> None:
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    create_migration("users", MigrationKind.EXISTING_TABLE, tmp_path, now=FIXED_NOW)

    assert existing_tables(tmp_path) == ["users"]


def test_existing_tables_ignores_unrelated_and_broken_files(tmp_path: Path) -> None:
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    migrations_dir = tmp_path / MIGRATIONS_DIR
    (migrations_dir / "notes.txt").write_text("posts")
    (migrations_dir / "__init__.py").write_text("")
    (migrations_dir / "broken.py").write_text("def (:")

    assert existing_tables(tmp_path) == ["users"]


# --- CLI ------------------------------------------------------------------


def test_cli_migration_for_a_new_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["migration"], input="2\nusers\n")

    assert result.exit_code == 0, result.output
    created = list((tmp_path / MIGRATIONS_DIR).glob("*_create_users_table.py"))
    assert len(created) == 1
    assert created[0].name in result.output


def test_cli_migration_binds_an_existing_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    create_migration("users", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)
    create_migration("posts", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW)

    result = CliRunner().invoke(app, ["migration"], input="1\n2\n")

    assert result.exit_code == 0, result.output
    # Tables are listed in sorted order, so option 2 is "users".
    assert "users" in result.output
    assert list((tmp_path / MIGRATIONS_DIR).glob("*_update_users_table.py"))


def test_cli_migration_existing_table_without_any_tables_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["migration"], input="1\n")

    assert result.exit_code == 1
    assert "No existing tables" in result.output


def test_cli_migration_reprompts_on_invalid_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["migration"], input="9\nx\n2\nuser-roles\nuser_roles\n")

    assert result.exit_code == 0, result.output
    assert list((tmp_path / MIGRATIONS_DIR).glob("*_create_user_roles_table.py"))
