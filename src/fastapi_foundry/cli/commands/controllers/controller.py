"""``fastapi-foundry controller``: create a controller class."""

import textwrap
from pathlib import Path

import typer

from fastapi_foundry.cli.prompts.controller import prompt_controller_name
from fastapi_foundry.generators.controller import (
    ControllerExistsError,
    create_controller,
    route_snippet,
)
from fastapi_foundry.generators.migration import NotAProjectError, ensure_project_root


def controller() -> None:
    """Create a controller class in the project's app/controller directory."""
    project_root = Path.cwd()

    # Check before prompting, so nothing is asked or written outside a project.
    try:
        ensure_project_root(project_root)
    except NotAProjectError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    controller_name = prompt_controller_name()

    try:
        controller_path = create_controller(controller_name, project_root)
    except ControllerExistsError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.secho(
        f"Created controller: {controller_path.relative_to(project_root).as_posix()}",
        fg=typer.colors.GREEN,
    )
    # app/routes.py is the user's file, so the route is shown rather than written.
    typer.echo("\nTo serve it, add a route to app/routes.py:\n")
    typer.echo(textwrap.indent(route_snippet(controller_name), "    "))
