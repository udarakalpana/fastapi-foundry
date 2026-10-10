"""``fastapi-foundry migration``: create a migration file."""

from pathlib import Path

import typer

from fastapi_foundry.cli.prompts.migration import (
    prompt_existing_table,
    prompt_migration_kind,
    prompt_new_table_name,
)
from fastapi_foundry.generators.migration import (
    MigrationKind,
    NotAProjectError,
    create_migration,
    ensure_project_root,
)


def migration() -> None:
    """Create a migration file in the project's migrations directory."""
    project_root = Path.cwd()

    # Check before prompting, so nothing is asked or written outside a project.
    try:
        ensure_project_root(project_root)
    except NotAProjectError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    kind = prompt_migration_kind()
    if kind is MigrationKind.EXISTING_TABLE:
        table = prompt_existing_table(project_root)
    else:
        table = prompt_new_table_name()

    migration_path = create_migration(table, kind, project_root)

    typer.secho(
        f"Created migration: {migration_path.relative_to(project_root)}",
        fg=typer.colors.GREEN,
    )
