"""``fastapi-foundry model``: create a model class."""

from pathlib import Path

import typer

from fastapi_foundry.cli.prompts.model import (
    prompt_model_for_existing_table,
    prompt_model_name,
    prompt_model_table,
)
from fastapi_foundry.generators.migration import NotAProjectError, ensure_project_root
from fastapi_foundry.generators.model import (
    ModelExistsError,
    create_model,
    model_name_for_table,
    table_name_for_model,
)


def model() -> None:
    """Create a model class in the project's app/model directory."""
    project_root = Path.cwd()

    # Check before prompting, so nothing is asked or written outside a project.
    try:
        ensure_project_root(project_root)
    except NotAProjectError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    if prompt_model_for_existing_table():
        table = prompt_model_table(project_root)
        model_name = prompt_model_name(default=model_name_for_table(table))
    else:
        model_name = prompt_model_name()
        table = table_name_for_model(model_name)

    try:
        model_path = create_model(model_name, table, project_root)
    except ModelExistsError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.secho(
        f"Created model: {model_path.relative_to(project_root).as_posix()} "
        f"(table '{table}')",
        fg=typer.colors.GREEN,
    )
