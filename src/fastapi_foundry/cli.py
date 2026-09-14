"""Command-line interface for fastapi-foundry.

This module only handles CLI concerns: argument parsing, user-facing output
and exit codes. All project-generation logic lives in ``fastapi_foundry.generators``.
"""

from pathlib import Path
from typing import Annotated

import typer

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
