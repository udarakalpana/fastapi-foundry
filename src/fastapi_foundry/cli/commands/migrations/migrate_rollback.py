"""``fastapi-foundry migrate:rollback``: revert the last batch of migrations."""

from fastapi_foundry.cli.commands.migrations._migrator import run_migrator_command
from fastapi_foundry.runner import MigratorAction


def migrate_rollback() -> None:
    """Revert the last batch of migrations."""
    run_migrator_command(MigratorAction.ROLLBACK)
