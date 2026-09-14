"""File templates for generated FastAPI projects.

Templates that depend on the project name use ``string.Template`` so that
braces in generated Python code (dicts, f-strings) need no escaping.
"""

from string import Template

FASTAPI_VERSION = "0.141.1"
UVICORN_VERSION = "0.53.0"
UV_BUILD_REQUIREMENT = "uv_build>=0.12.3,<0.13.0"

_PYPROJECT_TOML = Template('''\
[project]
name = "$distribution"
version = "0.1.0"
description = "A FastAPI application."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=$fastapi_version",
    "uvicorn[standard]>=$uvicorn_version",
]

[build-system]
requires = ["$uv_build_requirement"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "$package"
''')

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
uv run uvicorn $package.main:app --reload
```

To load settings from `.env`, add `--env-file .env`.

## URLs

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
''')

_PACKAGE_INIT = Template('''\
"""$distribution FastAPI application."""
''')

MAIN_PY = '''\
from fastapi import FastAPI

from . import config

app = FastAPI(title=config.APP_NAME, debug=config.DEBUG)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}
'''

_CONFIG_PY = Template('''\
"""Application configuration read from environment variables."""

import os

APP_NAME: str = os.getenv("APP_NAME", "$distribution")
DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
''')

DATABASE_INIT_PY = '''\
"""Database package."""
'''

DATABASE_CONNECTION_PY = '''\
"""Database connection setup.

Intentionally empty: the database layer will be added in a later phase.
"""
'''


def pyproject_toml(distribution: str, package: str) -> str:
    return _PYPROJECT_TOML.substitute(
        distribution=distribution,
        package=package,
        fastapi_version=FASTAPI_VERSION,
        uvicorn_version=UVICORN_VERSION,
        uv_build_requirement=UV_BUILD_REQUIREMENT,
    )


def env_file(distribution: str) -> str:
    return _ENV_FILE.substitute(distribution=distribution)


def readme(directory: str, package: str) -> str:
    return _README.substitute(directory=directory, package=package)


def package_init(distribution: str) -> str:
    return _PACKAGE_INIT.substitute(distribution=distribution)


def config_py(distribution: str) -> str:
    return _CONFIG_PY.substitute(distribution=distribution)
