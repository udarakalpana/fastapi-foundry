"""Shared helper for the commands that start the project's migration runner."""

from pathlib import Path

import typer

from fastapi_foundry.generators.migration import NotAProjectError
from fastapi_foundry.runner import (
    MigratorAction,
    MigratorNotFoundError,
    UvNotFoundError,
    run_migrator,
)


def run_migrator_command(action: MigratorAction) -> None:
    """Run the project's migration runner, exiting with its exit code."""
    try:
        exit_code = run_migrator(action, Path.cwd())
    except (NotAProjectError, MigratorNotFoundError, UvNotFoundError) as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    if exit_code != 0:
        raise typer.Exit(code=exit_code)
