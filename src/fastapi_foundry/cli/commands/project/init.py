"""``fastapi-foundry init``: create a new FastAPI project."""

from pathlib import Path
from typing import Annotated

import typer

from fastapi_foundry.generators.project import (
    InvalidProjectNameError,
    ProjectExistsError,
    ProjectName,
    create_project,
)


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
    typer.echo("\nNext steps:")
    typer.echo(f"  cd {project_path.name}")
    typer.echo("  uv sync")
    typer.echo("  uv run uvicorn app.routes:app --reload")
