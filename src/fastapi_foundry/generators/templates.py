"""File templates for generated FastAPI projects.

Templates that depend on the project name use ``string.Template`` so that
braces in generated Python code (dicts, f-strings) need no escaping.
"""

from string import Template

FASTAPI_VERSION = "0.141.1"
UVICORN_VERSION = "0.53.0"
SQLALCHEMY_VERSION = "2.0.54"
PYMYSQL_VERSION = "1.2.0"

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

## Run the application

```bash
uv run uvicorn app.routes:app --reload
```

To load settings from `.env`, add `--env-file .env`.

## URLs

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
''')

ROUTES_PY = '''\
"""Application routes."""

from fastapi import FastAPI

from app.config import APP_NAME, DEBUG
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

_CONFIG_PY = Template('''\
"""Application configuration read from environment variables."""

import os

APP_NAME: str = os.getenv("APP_NAME", "$distribution")
DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
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

DATABASE_CONNECTION_PY = '''\
"""Database connection setup.

Intentionally empty: the database layer will be added in a later phase.
"""
'''


def pyproject_toml(distribution: str) -> str:
    return _PYPROJECT_TOML.substitute(
        distribution=distribution,
        fastapi_version=FASTAPI_VERSION,
        uvicorn_version=UVICORN_VERSION,
        sqlalchemy_version=SQLALCHEMY_VERSION,
        pymysql_version=PYMYSQL_VERSION,
    )


def env_file(distribution: str) -> str:
    return _ENV_FILE.substitute(distribution=distribution)


def readme(directory: str) -> str:
    return _README.substitute(directory=directory)


def config_py(distribution: str) -> str:
    return _CONFIG_PY.substitute(distribution=distribution)


def migration_py(table: str, summary: str) -> str:
    return _MIGRATION_PY.substitute(table=table, summary=summary)
