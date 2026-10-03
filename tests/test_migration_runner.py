"""Tests for the migration runner that ``init`` writes to app/database/migrator.py.

The runner runs in a subprocess against a SQLite file, so the generically named
``app`` package stays out of this test session and no database server is needed.
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from fastapi_foundry.generators.migration import MIGRATIONS_DIR, MigrationKind, create_migration
from fastapi_foundry.generators.project import create_project

LATER = datetime(2099, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return create_project("myproject", parent_dir=tmp_path)


def _database_url(project_root: Path) -> str:
    return f"sqlite:///{project_root / 'test.sqlite'}"


def _run(project_root: Path, action: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": _database_url(project_root)}
    return subprocess.run(
        [sys.executable, "-m", "app.database.migrator", action],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )


def _tables(project_root: Path) -> set[str]:
    engine = create_engine(_database_url(project_root))
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _columns(project_root: Path, table: str) -> list[str]:
    engine = create_engine(_database_url(project_root))
    try:
        return [column["name"] for column in inspect(engine).get_columns(table)]
    finally:
        engine.dispose()


def _records(project_root: Path) -> list[tuple[str, int]]:
    engine = create_engine(_database_url(project_root))
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT migration, batch FROM foundry_migrations ORDER BY id")
            )
            return [tuple(row) for row in rows]
    finally:
        engine.dispose()


def _write_update_migration(project_root: Path, body_upgrade: str, body_downgrade: str) -> Path:
    path = create_migration("users", MigrationKind.EXISTING_TABLE, project_root, now=LATER)
    path.write_text(
        "from sqlalchemy import Column, String\n\n"
        "from app.database.schema import Schema\n\n"
        'TABLE = "users"\n\n\n'
        f"def upgrade(schema: Schema) -> None:\n    {body_upgrade}\n\n\n"
        f"def downgrade(schema: Schema) -> None:\n    {body_downgrade}\n"
    )
    return path


# --- migrate --------------------------------------------------------------


def test_migrate_creates_the_default_users_table(project: Path) -> None:
    result = _run(project, "migrate")

    assert result.returncode == 0, result.stderr
    assert {"users", "foundry_migrations"} <= _tables(project)
    assert _columns(project, "users") == ["id", "created_at", "updated_at"]
    [(name, batch)] = _records(project)
    assert name.endswith("_create_users_table")
    assert batch == 1
    assert name in result.stdout


def test_migrate_twice_does_nothing_the_second_time(project: Path) -> None:
    _run(project, "migrate")

    result = _run(project, "migrate")

    assert result.returncode == 0, result.stderr
    assert "Nothing to migrate" in result.stdout
    assert len(_records(project)) == 1


def test_each_migrate_run_gets_its_own_batch(project: Path) -> None:
    _run(project, "migrate")
    create_migration("posts", MigrationKind.NEW_TABLE, project, now=LATER)

    _run(project, "migrate")

    assert [batch for _, batch in _records(project)] == [1, 2]
    assert "posts" in _tables(project)


def test_migrations_run_in_timestamp_order(project: Path) -> None:
    create_migration("posts", MigrationKind.NEW_TABLE, project, now=LATER)
    _write_update_migration(
        project,
        'schema.add_column(TABLE, Column("phone", String(20), nullable=True))',
        'schema.drop_column(TABLE, "phone")',
    )

    result = _run(project, "migrate")

    assert result.returncode == 0, result.stderr
    names = [name for name, _ in _records(project)]
    assert names == sorted(names)
    assert "phone" in _columns(project, "users")


def test_toolkit_modules_are_not_run_as_migrations(project: Path) -> None:
    _run(project, "migrate")

    names = [name for name, _ in _records(project)]
    assert not any(name in {"schema", "migrator"} for name in names)


def test_a_failing_migration_stops_the_run_and_is_not_recorded(project: Path) -> None:
    _write_update_migration(project, 'raise RuntimeError("boom")', "pass")

    result = _run(project, "migrate")

    assert result.returncode == 1
    assert "boom" in result.stderr
    assert "update_users_table" in result.stderr
    # The users migration before it was applied and recorded; the failing one was not.
    names = [name for name, _ in _records(project)]
    assert len(names) == 1 and names[0].endswith("_create_users_table")


def test_error_is_printed_after_the_progress_lines_when_piped(project: Path) -> None:
    # CI logs pipe both streams into one; the error must follow the migration it is about.
    _write_update_migration(project, 'raise RuntimeError("boom")', "pass")
    env = {**os.environ, "DATABASE_URL": _database_url(project)}

    result = subprocess.run(
        [sys.executable, "-m", "app.database.migrator", "migrate"],
        cwd=project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    lines = result.stdout.splitlines()
    assert lines[-1].startswith("Error:")
    assert "update_users_table" in lines[-2]


# --- rollback -------------------------------------------------------------


def test_rollback_reverts_only_the_last_batch(project: Path) -> None:
    _run(project, "migrate")
    _write_update_migration(
        project,
        'schema.add_column(TABLE, Column("phone", String(20), nullable=True))',
        'schema.drop_column(TABLE, "phone")',
    )
    _run(project, "migrate")

    result = _run(project, "rollback")

    assert result.returncode == 0, result.stderr
    assert "phone" not in _columns(project, "users")
    assert "users" in _tables(project)
    assert [batch for _, batch in _records(project)] == [1]


def test_rollback_runs_the_batch_in_reverse_order(project: Path) -> None:
    _write_update_migration(
        project,
        'schema.add_column(TABLE, Column("phone", String(20), nullable=True))',
        'schema.drop_column(TABLE, "phone")',
    )
    _run(project, "migrate")

    # Dropping the column must happen before dropping the table, or this fails.
    result = _run(project, "rollback")

    assert result.returncode == 0, result.stderr
    assert "users" not in _tables(project)
    assert _records(project) == []


def test_rollback_with_nothing_applied(project: Path) -> None:
    result = _run(project, "rollback")

    assert result.returncode == 0, result.stderr
    assert "Nothing to roll back" in result.stdout


def test_migrate_after_rollback_reapplies(project: Path) -> None:
    _run(project, "migrate")
    _run(project, "rollback")

    result = _run(project, "migrate")

    assert result.returncode == 0, result.stderr
    assert "users" in _tables(project)
    assert [batch for _, batch in _records(project)] == [1]


def test_rollback_fails_clearly_when_a_migration_file_was_deleted(project: Path) -> None:
    _run(project, "migrate")
    for path in (project / MIGRATIONS_DIR).glob("*_create_users_table.py"):
        path.unlink()

    result = _run(project, "rollback")

    assert result.returncode == 1
    assert "create_users_table" in result.stderr
    assert len(_records(project)) == 1


# --- status and usage -----------------------------------------------------


def test_status_lists_applied_and_pending_migrations(project: Path) -> None:
    _run(project, "migrate")
    posts = create_migration("posts", MigrationKind.NEW_TABLE, project, now=LATER)

    result = _run(project, "status")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    users_line = next(line for line in lines if "create_users_table" in line)
    posts_line = next(line for line in lines if posts.stem in line)
    assert "Ran" in users_line and "1" in users_line
    assert "Pending" in posts_line


def test_unknown_action_prints_usage(project: Path) -> None:
    result = _run(project, "explode")

    assert result.returncode == 2
    assert "Usage" in result.stderr
