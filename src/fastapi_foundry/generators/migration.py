"""Generate migration files for an existing project.

Migrations live in a ``migrations/`` directory at the project root. Each file
records the table it targets in a module-level ``TABLE`` constant, which is how
:func:`existing_tables` discovers the tables earlier migrations already cover
without needing a database connection.
"""

import ast
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from fastapi_foundry.generators import templates

MIGRATIONS_DIR_NAME = "migrations"

# Unquoted SQL identifier rules, restricted further so the name is also safe to
# use in a filename: no path separators, dots or spaces.
_VALID_TABLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# MySQL's maximum identifier length.
_MAX_TABLE_NAME_LENGTH = 64

_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"


class InvalidTableNameError(ValueError):
    """Raised when a table name cannot be used safely."""


class MigrationKind(str, Enum):
    """Whether a migration creates a table or changes an existing one."""

    NEW_TABLE = "new"
    EXISTING_TABLE = "existing"

    @property
    def verb(self) -> str:
        """The word used in the migration's filename and docstring."""
        return "create" if self is MigrationKind.NEW_TABLE else "update"


def normalize_table_name(raw_name: str) -> str:
    """Return ``raw_name`` as a safe, lowercase table name.

    Raises:
        InvalidTableNameError: if the name is not a safe SQL identifier.
    """
    name = raw_name.strip()
    if not _VALID_TABLE_NAME.fullmatch(name):
        raise InvalidTableNameError(
            f"Invalid table name '{raw_name}'. Use letters, digits or '_', "
            "starting with a letter (e.g. 'users' or 'user_roles')."
        )
    if len(name) > _MAX_TABLE_NAME_LENGTH:
        raise InvalidTableNameError(
            f"Table name '{raw_name}' is longer than {_MAX_TABLE_NAME_LENGTH} characters."
        )
    return name.lower()


def migrations_dir(project_root: Path | None = None) -> Path:
    """Return the migrations directory for ``project_root``."""
    return (project_root or Path.cwd()) / MIGRATIONS_DIR_NAME


def existing_tables(project_root: Path | None = None) -> list[str]:
    """Return the sorted table names covered by existing migrations.

    Files that are not migrations, or that no longer parse because they were
    hand-edited, are skipped rather than failing the whole listing.
    """
    directory = migrations_dir(project_root)
    if not directory.is_dir():
        return []

    tables: set[str] = set()
    for migration_file in directory.glob("*.py"):
        table = _read_table_constant(migration_file)
        if table is not None:
            tables.add(table)
    return sorted(tables)


def create_migration(
    table_name: str,
    kind: MigrationKind,
    project_root: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Create a migration file and return its path.

    Raises:
        InvalidTableNameError: if ``table_name`` is not a safe table name.
    """
    table = normalize_table_name(table_name)
    timestamp = (now or datetime.now(timezone.utc)).strftime(_TIMESTAMP_FORMAT)

    directory = migrations_dir(project_root)
    directory.mkdir(parents=True, exist_ok=True)

    summary = f"{kind.verb.capitalize()} table '{table}'."
    content = templates.migration_py(table, summary)
    stem = f"{timestamp}_{kind.verb}_{table}_table"

    # "x" mode never overwrites, so a name taken within the same second is
    # retried with a counter instead of clobbering the earlier migration.
    for attempt in range(1, 100):
        suffix = "" if attempt == 1 else f"_{attempt}"
        migration_path = directory / f"{stem}{suffix}.py"
        try:
            with migration_path.open("x", encoding="utf-8") as file:
                file.write(content)
        except FileExistsError:
            continue
        return migration_path

    raise FileExistsError(f"Could not find a free migration filename for '{stem}'.")


def _read_table_constant(migration_file: Path) -> str | None:
    """Return the module-level ``TABLE`` string of a migration, if it has one."""
    try:
        module = ast.parse(migration_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None

    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = (t.id for t in node.targets if isinstance(t, ast.Name))
        if "TABLE" in targets and isinstance(node.value, ast.Constant):
            value = node.value.value
            if isinstance(value, str):
                return value
    return None
