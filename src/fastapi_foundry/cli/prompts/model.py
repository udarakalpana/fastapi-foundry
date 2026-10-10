"""Questions the ``model`` command asks before creating a model class."""

from pathlib import Path

import typer

from fastapi_foundry.cli.prompts.menu import prompt_index
from fastapi_foundry.generators.migration import MIGRATIONS_DIR, existing_tables
from fastapi_foundry.generators.model import InvalidModelNameError, normalize_model_name

_EXAMPLE_MODEL_NAME = "ProductModel"


def prompt_model_for_existing_table() -> bool:
    """Ask whether the model represents a table the migrations already create."""
    index = prompt_index("Is this model for an existing database table?", ["Yes", "No"])
    return index == 0


def prompt_model_table(project_root: Path) -> str:
    """Ask which of the already-migrated tables the model represents."""
    tables = existing_tables(project_root)
    if not tables:
        typer.secho(
            f"Error: No existing tables found in '{MIGRATIONS_DIR}/'. "
            "Create a migration for the table first, or answer 'No' to name a new model.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    return tables[prompt_index("Select the table this model represents", tables)]


def prompt_model_name(default: str | None = None) -> str:
    """Ask for a PascalCase model name, offering ``default`` if given."""
    example = default or _EXAMPLE_MODEL_NAME
    while True:
        # typer appends its own "[default]: " suffix, so the text is phrased without "?".
        raw_name = typer.prompt(f"Model name (PascalCase, e.g. {example})", default=default)
        try:
            return normalize_model_name(raw_name)
        except InvalidModelNameError as error:
            typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
