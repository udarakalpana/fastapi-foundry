"""Tests for how the ``fastapi_foundry.cli`` package is wired together.

The behaviour of each command is covered by the generator and runner tests;
these only check that the commands are registered, in order, from the module
that owns them, and that the packaged entry point still resolves.
"""

from importlib.metadata import entry_points

import typer
from typer.main import get_command
from typer.testing import CliRunner

from fastapi_foundry.cli import app

EXPECTED_COMMANDS = {
    "init": "fastapi_foundry.cli.commands.project.init",
    "migration": "fastapi_foundry.cli.commands.migrations.migration",
    "migrate": "fastapi_foundry.cli.commands.migrations.migrate",
    "migrate:rollback": "fastapi_foundry.cli.commands.migrations.migrate_rollback",
    "migrate:status": "fastapi_foundry.cli.commands.migrations.migrate_status",
    "model": "fastapi_foundry.cli.commands.models.model",
}


def _registered_commands() -> dict[str, str]:
    """Map each command name to the module its callback is defined in."""
    commands = get_command(app).commands
    return {name: command.callback.__module__ for name, command in commands.items()}


def test_commands_are_registered_in_order() -> None:
    assert list(_registered_commands()) == list(EXPECTED_COMMANDS)


def test_each_command_lives_in_its_own_module() -> None:
    assert _registered_commands() == EXPECTED_COMMANDS


def test_help_lists_every_command() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    for name in EXPECTED_COMMANDS:
        assert name in result.output


def test_console_script_entry_point_resolves_to_the_app() -> None:
    (entry_point,) = entry_points(group="console_scripts", name="fastapi-foundry")

    assert entry_point.value == "fastapi_foundry.cli:app"
    loaded = entry_point.load()
    assert isinstance(loaded, typer.Typer)
    assert loaded is app
