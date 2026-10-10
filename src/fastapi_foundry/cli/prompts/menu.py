"""A numbered-menu prompt that any command can reuse."""

from collections.abc import Sequence

import typer


def prompt_index(label: str, options: Sequence[str]) -> int:
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
