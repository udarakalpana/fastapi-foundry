"""``fastapi-foundry migrate:status``: show which migrations have run."""

from fastapi_foundry.cli.commands.migrations._migrator import run_migrator_command
from fastapi_foundry.runner import MigratorAction


def migrate_status() -> None:
    """List the project's migrations and whether each has run."""
    run_migrator_command(MigratorAction.STATUS)
