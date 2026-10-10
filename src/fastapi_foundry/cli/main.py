"""Builds the fastapi-foundry Typer app and registers its commands.

This is the only module that knows the command names; each command's
behaviour lives in ``fastapi_foundry.cli.commands`` and its interactive
questions in ``fastapi_foundry.cli.prompts``.
"""

import typer

from fastapi_foundry.cli.commands.migrations.migrate import migrate
from fastapi_foundry.cli.commands.migrations.migrate_rollback import migrate_rollback
from fastapi_foundry.cli.commands.migrations.migrate_status import migrate_status
from fastapi_foundry.cli.commands.migrations.migration import migration
from fastapi_foundry.cli.commands.models.model import model
from fastapi_foundry.cli.commands.project.init import init

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


# Registration order is the order `--help` lists the commands in.
app.command()(init)
app.command()(migration)
app.command()(migrate)
app.command("migrate:rollback")(migrate_rollback)
app.command("migrate:status")(migrate_status)
app.command()(model)
