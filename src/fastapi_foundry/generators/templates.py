"""File templates for generated FastAPI projects.

Templates that depend on the project name use ``string.Template`` so that
braces in generated Python code (dicts, f-strings) need no escaping.
"""

from string import Template

FASTAPI_VERSION = "0.141.1"
UVICORN_VERSION = "0.53.0"
SQLALCHEMY_VERSION = "2.0.54"
PYMYSQL_VERSION = "1.2.0"

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

_MIGRATION_PY = Template('''\
"""$summary"""

# Read by ``fastapi-foundry migration`` to list the tables that already exist.
TABLE = "$table"


def upgrade() -> None:
    """Apply this migration."""


def downgrade() -> None:
    """Revert this migration."""
''')

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


def migration_py(table: str, summary: str) -> str:
    return _MIGRATION_PY.substitute(table=table, summary=summary)
