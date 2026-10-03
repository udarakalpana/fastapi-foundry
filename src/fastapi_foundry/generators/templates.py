"""File templates for generated FastAPI projects.

Templates that depend on the project name use ``string.Template`` so that
braces in generated Python code (dicts, f-strings) need no escaping.
"""

from string import Template

FASTAPI_VERSION = "0.141.1"
UVICORN_VERSION = "0.53.0"
SQLALCHEMY_VERSION = "2.0.54"
PYMYSQL_VERSION = "1.2.0"
ALEMBIC_VERSION = "1.20.0"

# Points at a local MySQL server; projects change these through the DB_* variables.
DEFAULT_DB_CONNECTION = "mysql+pymysql"
DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USERNAME = "root"
DEFAULT_DB_PASSWORD = ""

_PYPROJECT_TOML = Template("""\
[project]
name = "$distribution"
version = "0.1.0"
description = "A FastAPI application."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=$fastapi_version",
    "uvicorn[standard]>=$uvicorn_version",
    "sqlalchemy>=$sqlalchemy_version",
    "pymysql>=$pymysql_version",
    "alembic>=$alembic_version",
]

# An application is deployed, not installed, so there is nothing to build.
[tool.uv]
package = false
""")

_ENV_FILE = Template('''\
APP_NAME=$distribution
DEBUG=false
DB_CONNECTION=$connection
DB_HOST=$host
DB_PORT=$port
DB_DATABASE=$database
DB_USERNAME=$username
DB_PASSWORD=$password
''')

GITIGNORE = '''\
# Python
__pycache__/
*.py[cod]
build/
dist/
*.egg-info/

# Virtual environments
.venv/

# Environment variables
.env

# Tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
'''

_README = Template('''\
# $directory

A FastAPI application.

## Install dependencies

```bash
uv sync
```

## Configure the environment

`.env` holds your local settings and is not committed. `.env.example` lists the same keys
and is committed, so after cloning the project create your own `.env` from it:

```bash
cp .env.example .env
```

When you add a setting, add its key to `.env.example` too.

## Run the application

```bash
uv run uvicorn app.routes:app --reload
```

To load settings from `.env`, add `--env-file .env`.

## Database

`app/config/database.py` builds the SQLAlchemy URL from the `DB_*` settings in `.env`
(MySQL via PyMySQL by default). Update them with your own credentials:

```text
DB_CONNECTION=mysql+pymysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=<database>
DB_USERNAME=<user>
DB_PASSWORD=<password>
```

Special characters in the username or password need no escaping. To use a complete
URL instead, set `DATABASE_URL`; it takes precedence over the `DB_*` settings.

Use `get_db` as a FastAPI dependency to get a session per request:

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.sqlalchemy_connection import get_db


@app.get("/items")
def list_items(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    ...
```

## URLs

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
''')

ROUTES_PY = '''\
"""Application routes."""

from fastapi import FastAPI

from app.config.app import APP_NAME, DEBUG
from app.controller.home_controller import HomeController

app = FastAPI(title=APP_NAME, debug=DEBUG)

home_controller = HomeController()


@app.get("/")
def root() -> dict[str, str]:
    return home_controller.index()
'''

HOME_CONTROLLER_PY = '''\
"""Controller for the application root."""


class HomeController:
    """Handles requests for the application root."""

    def index(self) -> dict[str, str]:
        return {"message": "Hello from fastapi-foundry"}
'''

_APP_CONFIG_PY = Template('''\
"""Application configuration read from environment variables."""

import os

APP_NAME: str = os.getenv("APP_NAME", "$distribution")
DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
''')

_DATABASE_CONFIG_PY = Template('''\
"""Database configuration read from environment variables."""

import os

from sqlalchemy.engine import URL

DB_CONNECTION: str = os.getenv("DB_CONNECTION", "$connection")
DB_HOST: str = os.getenv("DB_HOST", "$host")
DB_PORT: int = int(os.getenv("DB_PORT", "$port"))
DB_DATABASE: str = os.getenv("DB_DATABASE", "$database")
DB_USERNAME: str = os.getenv("DB_USERNAME", "$username")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "$password")

# URL.create escapes special characters in the username and password.
# A complete DATABASE_URL, if set, takes precedence over the DB_* settings.
DATABASE_URL: str = os.getenv("DATABASE_URL") or URL.create(
    drivername=DB_CONNECTION,
    username=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_DATABASE,
).render_as_string(hide_password=False)
''')

_CREATE_TABLE_MIGRATION_PY = Template('''\
"""$summary"""

from sqlalchemy import Column, Integer

from app.database.schema import Schema, timestamps

# Read by ``fastapi-foundry migration`` to list the tables that already exist.
TABLE = "$table"


def upgrade(schema: Schema) -> None:
    """Apply this migration."""
    schema.create_table(
        TABLE,
        Column("id", Integer, primary_key=True, autoincrement=True),
        *timestamps(),
    )


def downgrade(schema: Schema) -> None:
    """Revert this migration."""
    schema.drop_table(TABLE)
''')

_UPDATE_TABLE_MIGRATION_PY = Template('''\
"""$summary"""

from app.database.schema import Schema

# Read by ``fastapi-foundry migration`` to list the tables that already exist.
TABLE = "$table"


def upgrade(schema: Schema) -> None:
    """Apply this migration."""
    # For example (import Column and String from sqlalchemy):
    # schema.add_column(TABLE, Column("phone", String(20), nullable=True))


def downgrade(schema: Schema) -> None:
    """Revert this migration."""
    # Undo upgrade() in reverse order, for example:
    # schema.drop_column(TABLE, "phone")
''')

SCHEMA_PY = '''\
"""The operations a migration uses to change the database structure.

Every migration's ``upgrade()`` and ``downgrade()`` receive a ``Schema``. Make
structural changes through it rather than by importing your models, so each
migration stays a fixed record of one change however the models evolve.
"""

from collections.abc import Sequence
from typing import Any

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, DateTime, func
from sqlalchemy.engine import Connection


class Schema:
    """Changes the database structure, using Alembic to generate the SQL."""

    def __init__(self, connection: Connection) -> None:
        self._op = Operations(MigrationContext.configure(connection))

    def create_table(self, table: str, *columns: Column[Any]) -> None:
        self._op.create_table(table, *columns)

    def drop_table(self, table: str) -> None:
        self._op.drop_table(table)

    def rename_table(self, table: str, new_name: str) -> None:
        self._op.rename_table(table, new_name)

    def add_column(self, table: str, column: Column[Any]) -> None:
        self._op.add_column(table, column)

    def drop_column(self, table: str, column: str) -> None:
        self._op.drop_column(table, column)

    def alter_column(self, table: str, column: str, **changes: Any) -> None:
        """Change a column, e.g. ``nullable=False`` or ``new_column_name="email"``.

        MySQL needs the column's current type for most changes, so pass
        ``existing_type`` too. The keywords are those of Alembic's ``alter_column``.
        """
        self._op.alter_column(table, column, **changes)

    def create_index(self, table: str, columns: Sequence[str], *, unique: bool = False) -> None:
        self._op.create_index(index_name(table, columns), table, list(columns), unique=unique)

    def drop_index(self, table: str, columns: Sequence[str]) -> None:
        self._op.drop_index(index_name(table, columns), table_name=table)

    def execute(self, sql: str) -> None:
        """Run raw SQL, e.g. to backfill data after adding a column."""
        self._op.execute(sql)


def index_name(table: str, columns: Sequence[str]) -> str:
    """The name ``create_index`` gives an index, so ``drop_index`` can find it."""
    return f"ix_{table}_{'_'.join(columns)}"


def timestamps() -> tuple[Column[Any], Column[Any]]:
    """``created_at`` and ``updated_at`` columns that default to the current time."""
    return (
        Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
        Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    )
'''

MIGRATOR_PY = '''\
"""Apply and roll back the migrations in app/database/.

Run from the project root (``fastapi-foundry migrate`` does this for you):

    python -m app.database.migrator migrate    # apply pending migrations
    python -m app.database.migrator rollback   # revert the last batch
    python -m app.database.migrator status     # list migrations and their state

Applied migrations are recorded in the ``foundry_migrations`` table. Each
``migrate`` run is one batch, and ``rollback`` reverts the latest batch.
"""

import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from sqlalchemy import Column, Integer, MetaData, String, Table, delete, insert, select
from sqlalchemy.engine import Connection

from app.config.sqlalchemy_connection import engine
from app.database.schema import Schema

MIGRATIONS_DIR = Path(__file__).resolve().parent

# Migration files start with the timestamp ``fastapi-foundry migration`` gives
# them, which also orders them. Other modules here, like this one, are skipped.
_MIGRATION_FILE = re.compile(r"^\\d{14}_\\w+\\.py$")

_metadata = MetaData()
migrations_table = Table(
    "foundry_migrations",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("migration", String(255), nullable=False, unique=True),
    Column("batch", Integer, nullable=False),
)


class MigrationError(Exception):
    """Raised when a migration cannot be loaded or fails to run."""


def migration_names() -> list[str]:
    """Return the names of all migration files, oldest first."""
    return sorted(
        path.stem for path in MIGRATIONS_DIR.glob("*.py") if _MIGRATION_FILE.fullmatch(path.name)
    )


def migrate() -> int:
    applied = _applied()
    pending = [name for name in migration_names() if name not in applied]
    if not pending:
        print("Nothing to migrate.")
        return 0

    batch = max(applied.values(), default=0) + 1
    for name in pending:
        print(f"Migrating:    {name}")
        # One transaction per migration. On databases where DDL is
        # transactional a failed migration is undone; MySQL commits each DDL
        # statement immediately, so check the database after a failure there.
        with engine.begin() as connection:
            _run_step(name, "upgrade", connection)
            connection.execute(insert(migrations_table).values(migration=name, batch=batch))
        print(f"Migrated:     {name}")
    return 0


def rollback() -> int:
    applied = _applied()
    if not applied:
        print("Nothing to roll back.")
        return 0

    last_batch = max(applied.values())
    for name in sorted((n for n, b in applied.items() if b == last_batch), reverse=True):
        print(f"Rolling back: {name}")
        with engine.begin() as connection:
            _run_step(name, "downgrade", connection)
            connection.execute(delete(migrations_table).where(migrations_table.c.migration == name))
        print(f"Rolled back:  {name}")
    return 0


def status() -> int:
    applied = _applied()
    names = sorted(set(migration_names()) | set(applied))
    if not names:
        print("No migrations found.")
        return 0

    print(f"{'Status':<9}{'Batch':<7}Migration")
    for name in names:
        batch = applied.get(name)
        state = "Pending" if batch is None else "Ran"
        print(f"{state:<9}{'' if batch is None else batch:<7}{name}")
    return 0


def _applied() -> dict[str, int]:
    """Return applied migrations and their batch, creating the table if needed."""
    _metadata.create_all(engine)
    with engine.connect() as connection:
        rows = connection.execute(select(migrations_table.c.migration, migrations_table.c.batch))
        return {name: batch for name, batch in rows}


def _run_step(name: str, step: str, connection: Connection) -> None:
    try:
        function: Callable[[Schema], None] = getattr(_load(name), step)
        function(Schema(connection))
    except Exception as error:
        raise MigrationError(f"{name}: {error}") from error


def _load(name: str) -> ModuleType:
    path = MIGRATIONS_DIR / f"{name}.py"
    if not path.is_file():
        raise MigrationError(f"migration file '{path.name}' not found in app/database/")
    # Migration names start with a digit, so they are loaded by path, not imported.
    spec = importlib.util.spec_from_file_location(f"migration_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ACTIONS: dict[str, Callable[[], int]] = {
    "migrate": migrate,
    "rollback": rollback,
    "status": status,
}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _ACTIONS:
        print(f"Usage: python -m app.database.migrator {{{'|'.join(_ACTIONS)}}}", file=sys.stderr)
        return 2
    try:
        return _ACTIONS[args[0]]()
    except MigrationError as error:
        # Flush progress first, so a piped log shows the error after it.
        sys.stdout.flush()
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

SQLALCHEMY_CONNECTION_PY = '''\
"""SQLAlchemy engine and per-request sessions."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.app import DEBUG
from app.config.database import DATABASE_URL

# Connections are opened lazily, so the app starts even if the database is down.
# pool_pre_ping replaces connections the server has dropped while idle.
engine = create_engine(DATABASE_URL, echo=DEBUG, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Yield a session for one request and close it when the request ends."""
    with SessionLocal() as session:
        yield session
'''


def pyproject_toml(distribution: str) -> str:
    return _PYPROJECT_TOML.substitute(
        distribution=distribution,
        fastapi_version=FASTAPI_VERSION,
        uvicorn_version=UVICORN_VERSION,
        sqlalchemy_version=SQLALCHEMY_VERSION,
        pymysql_version=PYMYSQL_VERSION,
        alembic_version=ALEMBIC_VERSION,
    )


def env_file(distribution: str, database: str) -> str:
    return _ENV_FILE.substitute(distribution=distribution, **_db_settings(database))


def readme(directory: str) -> str:
    return _README.substitute(directory=directory)


def app_config_py(distribution: str) -> str:
    return _APP_CONFIG_PY.substitute(distribution=distribution)


def database_config_py(database: str) -> str:
    return _DATABASE_CONFIG_PY.substitute(**_db_settings(database))


def _db_settings(database: str) -> dict[str, object]:
    """Default DB_* values, shared by .env and app/config/database.py."""
    return {
        "connection": DEFAULT_DB_CONNECTION,
        "host": DEFAULT_DB_HOST,
        "port": DEFAULT_DB_PORT,
        "database": database,
        "username": DEFAULT_DB_USERNAME,
        "password": DEFAULT_DB_PASSWORD,
    }


def create_table_migration_py(table: str, summary: str) -> str:
    return _CREATE_TABLE_MIGRATION_PY.substitute(table=table, summary=summary)


def update_table_migration_py(table: str, summary: str) -> str:
    return _UPDATE_TABLE_MIGRATION_PY.substitute(table=table, summary=summary)
