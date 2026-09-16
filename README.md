# fastapi-foundry

[![PyPI version](https://img.shields.io/pypi/v/fastapi-foundry)](https://pypi.org/project/fastapi-foundry/)
[![Python versions](https://img.shields.io/pypi/pyversions/fastapi-foundry)](https://pypi.org/project/fastapi-foundry/)
[![License: MIT](https://img.shields.io/pypi/l/fastapi-foundry)](https://github.com/udarakalpana/fastapi-foundry/blob/master/LICENSE)

**fastapi-foundry** is a command-line tool that scaffolds new [FastAPI](https://fastapi.tiangolo.com/) projects in seconds.

One command gives you a ready-to-run FastAPI application with a clean `src/` layout,
a modern [uv](https://docs.astral.sh/uv/)-compatible `pyproject.toml`, environment-based
configuration and a sensible `.gitignore`, so you can skip the boilerplate and start
building your API.

```bash
uvx fastapi-foundry init myproject
```

## Features

- **One-command setup**: `fastapi-foundry init <name>` creates a complete project.
- **Runs immediately**: the generated app starts with `uv sync` and `uvicorn`, no edits needed.
- **Modern packaging**: `src/` layout, `pyproject.toml` and the `uv_build` backend.
- **Safe by default**: never overwrites an existing directory and rejects unsafe project names.
- **Friendly names**: `my-api` becomes the `my-api/` folder with an importable `my_api` package.
- **Database ready**: SQLAlchemy and PyMySQL are included so you can connect to MySQL right away.

## Requirements

- Python **3.12** or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

Install uv if you don't have it yet:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation

### Option 1: Run without installing (recommended)

`uvx` downloads and runs the latest version in a temporary environment:

```bash
uvx fastapi-foundry init myproject
```

### Option 2: Install as a global command

```bash
uv tool install fastapi-foundry
```

Then use it from any directory:

```bash
fastapi-foundry init myproject
```

Upgrade later with:

```bash
uv tool upgrade fastapi-foundry
```

### Option 3: Install with pip

```bash
pip install fastapi-foundry
```

## Quick start

**1. Create a project**

```bash
uvx fastapi-foundry init myproject
```

```text
Created FastAPI project: myproject

Next steps:
  cd myproject
  uv sync
  uv run uvicorn myproject.main:app --reload
```

**2. Install dependencies**

```bash
cd myproject
uv sync
```

**3. Run the application**

```bash
uv run uvicorn myproject.main:app --reload
```

**4. Open it in your browser**

| URL | Description |
|---|---|
| http://127.0.0.1:8000 | API root, returns `{"message": "Hello from FastAPI"}` |
| http://127.0.0.1:8000/docs | Interactive Swagger UI documentation |
| http://127.0.0.1:8000/redoc | ReDoc documentation |

## Generated project structure

```text
myproject/
├── pyproject.toml        # Project metadata and dependencies (FastAPI, Uvicorn, SQLAlchemy, PyMySQL)
├── .env                  # Environment variables
├── .gitignore            # Python, uv and tooling ignores
├── README.md             # How to install and run the project
└── src/
    └── myproject/
        ├── __init__.py
        ├── main.py       # FastAPI application
        ├── config.py     # Settings read from environment variables
        └── database/
            ├── __init__.py
            └── connection.py
```

The generated `main.py`:

```python
from fastapi import FastAPI

from . import config

app = FastAPI(title=config.APP_NAME, debug=config.DEBUG)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}
```

## Configuration

Generated projects read their settings from environment variables in `config.py`:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | project name | Title shown in the API docs |
| `DEBUG` | `false` | Enables FastAPI debug mode (`true`, `1` or `yes`) |

To load the values from the generated `.env` file, start the server with `--env-file`:

```bash
uv run uvicorn myproject.main:app --reload --env-file .env
```

## Project names

The project name is used for both the folder and the Python package, so it must:

- start with a letter
- contain only letters, digits, hyphens (`-`) and underscores (`_`)
- not be a Python keyword or clash with a standard library or FastAPI module (for example `json` or `fastapi`)

Hyphens are converted for the package name:

```bash
uvx fastapi-foundry init my-fastapi-app
```

This creates the `my-fastapi-app/` folder containing the `my_fastapi_app` package, which you run with:

```bash
uv run uvicorn my_fastapi_app.main:app --reload
```

If the target folder already exists, fastapi-foundry stops with an error instead of overwriting your files.

## Command reference

```bash
fastapi-foundry --help          # Show available commands
fastapi-foundry init --help     # Show help for the init command
fastapi-foundry init <name>     # Create a new project in the current directory
```

## Roadmap

fastapi-foundry is in early development. Planned features include:

- Database setup with SQLAlchemy and Alembic migrations
- Settings management with Pydantic Settings
- Generators for models and routes
- Authentication scaffolding
- Docker support

## Contributing

Issues and pull requests are welcome on [GitHub](https://github.com/udarakalpana/fastapi-foundry/issues).

To set up a development environment:

```bash
git clone https://github.com/udarakalpana/fastapi-foundry.git
cd fastapi-foundry
uv sync
uv run pytest
```

Run the CLI from your local checkout:

```bash
uv run fastapi-foundry init myproject
```

Tip: create test projects outside the repository folder so they don't get mixed into its Git history.

## License

fastapi-foundry is released under the [MIT License](https://github.com/udarakalpana/fastapi-foundry/blob/master/LICENSE).
