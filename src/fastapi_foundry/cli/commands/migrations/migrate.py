"""``fastapi-foundry migrate``: apply pending migrations."""

from fastapi_foundry.cli.commands.migrations._migrator import run_migrator_command
from fastapi_foundry.runner import MigratorAction


def migrate() -> None:
    """Apply the project's pending migrations to the database."""
    run_migrator_command(MigratorAction.MIGRATE)
