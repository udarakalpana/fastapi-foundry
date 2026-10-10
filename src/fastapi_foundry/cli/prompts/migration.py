"""Questions the ``migration`` command asks before creating a migration file."""

from pathlib import Path

import typer

from fastapi_foundry.cli.prompts.menu import prompt_index
from fastapi_foundry.generators.migration import (
    MIGRATIONS_DIR,
    InvalidTableNameError,
    MigrationKind,
    existing_tables,
    normalize_table_name,
)


def prompt_migration_kind() -> MigrationKind:
    """Ask whether the migration targets an existing table or a new one."""
    kinds = [MigrationKind.EXISTING_TABLE, MigrationKind.NEW_TABLE]
    index = prompt_index(
        "Is this migration for an existing table or a new table?",
        ["Existing table", "New table"],
    )
    return kinds[index]


def prompt_existing_table(project_root: Path) -> str:
    """Ask which of the already-migrated tables to bind this migration to."""
    tables = existing_tables(project_root)
    if not tables:
        typer.secho(
            f"Error: No existing tables found in '{MIGRATIONS_DIR}/'. "
            "Create a migration for a new table first.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    return tables[prompt_index("Select the table to bind this migration to", tables)]


def prompt_new_table_name() -> str:
    """Ask for the name of the table this migration will structure."""
    while True:
        # typer appends its own ": " suffix, so the text is phrased without "?".
        raw_name = typer.prompt(
            "What is the name of the table this migration should structure"
        )
        try:
            return normalize_table_name(raw_name)
        except InvalidTableNameError as error:
            typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
