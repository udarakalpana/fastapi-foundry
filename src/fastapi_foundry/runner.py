"""Run a project's migrations inside the project's own environment.

Applying migrations needs the project's dependencies (SQLAlchemy, Alembic, the
database driver) and its settings, none of which fastapi-foundry installs. So
the work is done by the project's ``app/database/migrator.py``, started with
``uv run``; this module only checks the project and launches it.
"""

import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path

from fastapi_foundry.generators.migration import ensure_project_root

MIGRATOR = Path("app", "database", "migrator.py")
MIGRATOR_MODULE = "app.database.migrator"


class MigratorNotFoundError(Exception):
    """Raised when the project has no migration runner."""


class UvNotFoundError(Exception):
    """Raised when uv, which runs the project's environment, is not installed."""


class MigratorAction(str, Enum):
    """What the project's migration runner should do."""

    MIGRATE = "migrate"
    ROLLBACK = "rollback"
    STATUS = "status"


def migrator_command(action: MigratorAction, project_root: Path) -> list[str]:
    """Return the command that runs ``action`` in the project's environment."""
    command = ["uv", "run"]
    # The generated app reads its settings from environment variables only.
    if (project_root / ".env").is_file():
        command += ["--env-file", ".env"]
    return [*command, "python", "-m", MIGRATOR_MODULE, action.value]


def run_migrator(action: MigratorAction, project_root: Path | None = None) -> int:
    """Run the project's migration runner and return its exit code.

    Raises:
        NotAProjectError: if ``project_root`` is not a project root.
        MigratorNotFoundError: if the project has no ``app/database/migrator.py``.
        UvNotFoundError: if ``uv`` is not installed.
    """
    root = project_root or Path.cwd()
    ensure_project_root(root)

    if not (root / MIGRATOR).is_file():
        raise MigratorNotFoundError(
            f"'{MIGRATOR.as_posix()}' not found. Projects created before migrations could "
            "run don't have it; create a new project with `fastapi-foundry init` and copy "
            "its app/database/schema.py and app/database/migrator.py into this one."
        )
    if shutil.which("uv") is None:
        raise UvNotFoundError(
            "uv is required to run migrations in the project's environment "
            "(https://docs.astral.sh/uv/). Without uv, activate the project's virtual "
            f"environment and run `python -m {MIGRATOR_MODULE} {action.value}`."
        )

    # fastapi-foundry's own environment may be active; uv should use the project's.
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    return subprocess.run(migrator_command(action, root), cwd=root, env=env).returncode
