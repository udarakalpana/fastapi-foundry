"""Command-line interface for fastapi-foundry.

This module only handles CLI concerns: argument parsing, user-facing output
and exit codes. All project-generation logic lives in ``fastapi_foundry.generators``.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from fastapi_foundry.generators.migration import (
    MIGRATIONS_DIR_NAME,
    InvalidTableNameError,
    MigrationKind,
    create_migration,
    existing_tables,
    normalize_table_name,
)
from fastapi_foundry.generators.project import (
    InvalidProjectNameError,
    ProjectExistsError,
    ProjectName,
    create_project,
)

app = typer.Typer(
    help="Scaffold FastAPI projects.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Scaffold FastAPI projects."""
    # Defining a callback keeps `init` as an explicit subcommand, so more
    # commands can be added later without changing the CLI shape.


@app.command()
def init(
    name: Annotated[
        str,
        typer.Argument(help="Project name, e.g. 'myproject' or 'my-fastapi-app'."),
    ],
) -> None:
    """Create a new FastAPI project in the current directory."""
    try:
        project_name = ProjectName.from_raw(name)
        project_path = create_project(project_name, parent_dir=Path.cwd())
    except (InvalidProjectNameError, ProjectExistsError) as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.secho(
        f"Created FastAPI project: {project_name.directory}",
        fg=typer.colors.GREEN,
    )
    if project_name.package != project_name.directory:
        typer.echo(f"Python package name: {project_name.package}")

    typer.echo("\nNext steps:")
    typer.echo(f"  cd {project_path.name}")
    typer.echo("  uv sync")
    typer.echo(f"  uv run uvicorn {project_name.package}.main:app --reload")


@app.command()
def migration() -> None:
    """Create a migration file in the project's migrations directory."""
    project_root = Path.cwd()

    kind = _prompt_migration_kind()
    if kind is MigrationKind.EXISTING_TABLE:
        table = _prompt_existing_table(project_root)
    else:
        table = _prompt_new_table_name()

    migration_path = create_migration(table, kind, project_root)

    typer.secho(
        f"Created migration: {migration_path.relative_to(project_root)}",
        fg=typer.colors.GREEN,
    )


def _prompt_migration_kind() -> MigrationKind:
    """Ask whether the migration targets an existing table or a new one."""
    kinds = [MigrationKind.EXISTING_TABLE, MigrationKind.NEW_TABLE]
    index = _prompt_index(
        "Is this migration for an existing table or a new table?",
        ["Existing table", "New table"],
    )
    return kinds[index]


def _prompt_existing_table(project_root: Path) -> str:
    """Ask which of the already-migrated tables to bind this migration to."""
    tables = existing_tables(project_root)
    if not tables:
        typer.secho(
            f"Error: No existing tables found in '{MIGRATIONS_DIR_NAME}/'. "
            "Create a migration for a new table first.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    return tables[_prompt_index("Select the table to bind this migration to", tables)]


def _prompt_new_table_name() -> str:
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


def _prompt_index(label: str, options: Sequence[str]) -> int:
    """Show a numbered menu and return the zero-based index the user picked."""
    typer.echo(f"\n{label}")
    for number, option in enumerate(options, start=1):
        typer.echo(f"  {number}) {option}")

    while True:
        answer = typer.prompt(f"Select [1-{len(options)}]")
        try:
            selected = int(answer)
        except ValueError:
            selected = 0
        if 1 <= selected <= len(options):
            return selected - 1
        typer.secho(
            f"Error: Enter a number between 1 and {len(options)}.",
            fg=typer.colors.RED,
            err=True,
        )
