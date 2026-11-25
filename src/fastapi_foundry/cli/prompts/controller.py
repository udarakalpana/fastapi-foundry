"""Questions the ``controller`` command asks before creating a controller class."""

import typer

from fastapi_foundry.generators.controller import (
    InvalidControllerNameError,
    normalize_controller_name,
)

_EXAMPLE_CONTROLLER_NAME = "ProductController"


def prompt_controller_name() -> str:
    """Ask for a PascalCase controller name until a valid one is given."""
    while True:
        raw_name = typer.prompt(f"Controller name (PascalCase, e.g. {_EXAMPLE_CONTROLLER_NAME})")
        try:
            return normalize_controller_name(raw_name)
        except InvalidControllerNameError as error:
            typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
