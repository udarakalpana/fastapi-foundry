"""Tests for the migration toolkit that ``init`` writes and the migration templates."""

import ast
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from fastapi_foundry.generators.migration import (
    MigrationKind,
    create_migration,
    existing_tables,
)
from fastapi_foundry.generators.project import create_project
from fastapi_foundry.generators.templates import ALEMBIC_VERSION

FIXED_NOW = datetime(2026, 10, 3, 9, 0, 0, tzinfo=timezone.utc)


def _function(source: str, name: str) -> ast.FunctionDef:
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name}() not defined")


def _parameters(function: ast.FunctionDef) -> list[str]:
    return [argument.arg for argument in function.args.args]


# --- generated project ----------------------------------------------------


def test_init_writes_the_schema_and_migrator_modules(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert (project_root / "app" / "database" / "schema.py").is_file()
    assert (project_root / "app" / "database" / "migrator.py").is_file()


def test_generated_project_depends_on_alembic(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())

    assert f"alembic>={ALEMBIC_VERSION}" in pyproject["project"]["dependencies"]


def test_toolkit_modules_are_not_listed_as_tables(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert existing_tables(project_root) == ["users"]


# --- migration templates --------------------------------------------------


def test_new_table_migration_creates_and_drops_the_table(tmp_path: Path) -> None:
    source = create_migration("posts", MigrationKind.NEW_TABLE, tmp_path, now=FIXED_NOW).read_text()

    upgrade = _function(source, "upgrade")
    downgrade = _function(source, "downgrade")
    assert _parameters(upgrade) == ["schema"]
    assert _parameters(downgrade) == ["schema"]
    assert "schema.create_table(" in ast.get_source_segment(source, upgrade)
    assert "*timestamps()" in ast.get_source_segment(source, upgrade)
    assert "schema.drop_table(TABLE)" in ast.get_source_segment(source, downgrade)
    assert 'TABLE = "posts"' in source


def test_existing_table_migration_takes_a_schema_and_changes_nothing_yet(tmp_path: Path) -> None:
    source = create_migration("posts", MigrationKind.EXISTING_TABLE, tmp_path, now=FIXED_NOW).read_text()

    for name in ("upgrade", "downgrade"):
        function = _function(source, name)
        assert _parameters(function) == ["schema"]
        # Only a docstring: examples are comments, so nothing runs until edited.
        assert len(function.body) == 1
    assert "schema.add_column" in source
    assert 'TABLE = "posts"' in source


def test_both_templates_compile(tmp_path: Path) -> None:
    for kind in MigrationKind:
        path = create_migration("posts", kind, tmp_path, now=FIXED_NOW)
        compile(path.read_text(), str(path), "exec")
