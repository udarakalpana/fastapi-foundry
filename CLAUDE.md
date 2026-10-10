# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

**fastapi-foundry** is a Typer CLI, published to PyPI, that scaffolds FastAPI projects and
manages their migrations. It is a *code generator*: most of the code here is templates for
files that end up in someone else's project. A change is only correct if the **generated
project still installs, imports and runs**, not just if this package's own code works.

- Python `>=3.12` (CI tests 3.12, 3.13, 3.14; local default in `.python-version` is 3.14)
- Build backend `uv_build`; dependencies and tooling managed with `uv`
- Runtime dependency: `typer` only. Everything else (FastAPI, SQLAlchemy, Alembic, PyMySQL,
  httpx, python-dotenv) is in the `dev` group so tests can execute the generated code.

## Commands

```bash
uv sync                                   # install the package and dev dependencies
uv run pytest                             # run the full suite
uv run pytest tests/runner                # run one area
uv run pytest -k migrate_twice            # run tests by name
uv run --locked pytest                    # what CI runs; fails if uv.lock is stale
uv run fastapi-foundry init myproject     # run the CLI from this checkout
```

Create throwaway projects **outside** the repository so they don't end up in Git.

## Architecture

The code is layered; dependencies only point downward.

```text
cli/main.py                 builds the Typer app, registers command names (only place that knows them)
   │
cli/commands/<area>/*.py    one module per command: parse args, call a generator/runner,
   │                        print coloured output, map domain errors to `typer.Exit(code=1)`
cli/prompts/*.py            interactive questions; return validated values, re-ask on bad input
   │
generators/project.py       ProjectName validation + create_project()
generators/migration.py     table-name validation, project-root check, create_migration(),
   │                        existing_tables()
generators/templates.py     the text of every generated file (no logic beyond substitution)
runner.py                   launches the generated project's own migrator via `uv run`
```

Layer rules:

- **`cli/` contains no generation logic.** It never touches the filesystem except through
  generators/runner, and is the only layer that prints or calls `typer.Exit`.
- **Generators and runner never import Typer or print.** They raise domain exceptions
  (`InvalidProjectNameError`, `ProjectExistsError`, `InvalidTableNameError`,
  `NotAProjectError`, `MigratorNotFoundError`, `UvNotFoundError`) with user-ready messages;
  the command module catches them and shows `Error: <message>` on stderr.
- **Generator functions take an explicit path** (`parent_dir`, `project_root`, and `now` for
  timestamps), defaulting to `Path.cwd()` / current time. Tests always pass them explicitly.
- **Migrations run in the generated project's environment, not ours.** fastapi-foundry does
  not depend on SQLAlchemy/Alembic at runtime, so `migrate`, `migrate:rollback` and
  `migrate:status` call `runner.run_migrator()`, which runs
  `uv run [--env-file .env] python -m app.database.migrator <action>` in the project root
  (with `VIRTUAL_ENV` stripped). The real migration logic is the `MIGRATOR_PY` and
  `SCHEMA_PY` templates written into each project.

### Invariants to preserve

- **Never overwrite user files.** Project and migration files are opened with mode `"x"`;
  `create_project` refuses an existing directory and removes only the directory *it* created
  if writing fails. Same-second migration names get a `_2`, `_3`… suffix.
- **Validate names before using them in paths.** Project names: `^[A-Za-z][A-Za-z0-9_-]*$`,
  not a keyword, stdlib module or reserved package (`fastapi`, `tests`, …). Table names:
  `^[A-Za-z][A-Za-z0-9_]*$`, max 64 chars, lowercased.
- **Commands that work on a project check the root first** (`ensure_project_root`: needs
  `pyproject.toml` and `app/routes.py`) *before* prompting or writing anything.
- **Migrations are discovered without a database**: each file has a module-level
  `TABLE = "<name>"` constant read with `ast`, and a `YYYYMMDDHHMMSS_<verb>_<table>_table.py`
  filename that also defines run order.
- The default `users` migration in a new project is written by `create_migration()`, so it is
  byte-identical to one made by `fastapi-foundry migration`.

### Templates (`generators/templates.py`)

- Fixed files are plain string constants (`ROUTES_PY`, `SCHEMA_PY`, `MIGRATOR_PY`, …).
  Name-dependent files use `string.Template` (`$name`) behind a small function
  (`pyproject_toml()`, `env_file()`, …) so braces in generated Python need no escaping.
- Backslashes inside the triple-quoted templates are escaped (`\\d`), because the template
  is itself a Python string.
- Dependency floors for generated projects live in the `*_VERSION` constants. Keep the
  matching packages in this repo's `dev` group at the same versions, since tests run the
  generated code against them.
- `.env` and `.env.example` are generated from the same template; a new setting must be
  added to the `_ENV_FILE` template, the relevant `app/config/*.py` template and the README.

## Directory structure

```text
.
├── pyproject.toml              # package metadata, `fastapi-foundry` console script, pytest config
├── uv.lock                     # committed; CI runs with --locked
├── README.md                   # user docs, also the PyPI page; keep in sync with behaviour
├── .github/workflows/
│   ├── tests.yml               # pytest on PRs to master, Python 3.12–3.14 matrix
│   └── publish.yml             # PyPI release
├── src/fastapi_foundry/
│   ├── cli/
│   │   ├── __init__.py         # exports `app` (the console-script target)
│   │   ├── main.py             # Typer app + command registration, in --help order
│   │   ├── commands/
│   │   │   ├── project/init.py
│   │   │   └── migrations/     # migration.py, migrate.py, migrate_rollback.py,
│   │   │                       # migrate_status.py, _migrator.py (shared helper)
│   │   └── prompts/            # menu.py (numbered menu), migration.py
│   ├── generators/             # project.py, migration.py, templates.py
│   └── runner.py               # starts the project's migrator
└── tests/                      # mirrors src/ by area
    ├── cli/                    # command registration and entry point
    ├── generators/
    │   ├── project/            # one file per project feature (config, env, database, …)
    │   └── migration/          # generator, templates, project-root check, table discovery
    └── runner/                 # migrate commands (subprocess faked) and the real migrator
```

What a generated project looks like (flat `app/` namespace package, no `__init__.py`, no
`[build-system]`, run with `uvicorn app.routes:app`):

```text
myproject/
├── pyproject.toml  .env  .env.example  .gitignore  README.md
└── app/
    ├── routes.py                     # FastAPI app; thin routes delegating to controllers
    ├── controller/home_controller.py
    ├── config/                       # app.py, database.py, sqlalchemy_connection.py
    └── database/                     # schema.py, migrator.py, <timestamp>_create_users_table.py
```

### Adding a command

1. Write the tests first (see below), including adding it to `EXPECTED_COMMANDS` in
   `tests/cli/test_cli_structure.py`.
2. Put the logic in `generators/` (or `runner.py`) with explicit-path parameters and domain
   exceptions.
3. Add `cli/commands/<area>/<command>.py` with a function named after the command, and any
   questions in `cli/prompts/`.
4. Register it in `cli/main.py` (use `app.command("name:sub")(fn)` for colon names).
5. Document it in `README.md` (feature list, command reference and its own section).

## Testing approach: TDD

All feature work and bug fixes follow **red → green → refactor**:

1. **Red** – write the tests first, in a **new test file** for the feature under the matching
   `tests/<area>/` folder (don't append unrelated tests to an existing file). Run them and
   confirm they fail *for the right reason* (usually `ImportError` / missing attribute /
   assertion on missing file), not because of a typo in the test.
2. **Green** – implement the smallest change that makes them pass. Run the whole suite.
3. **Refactor** – clean up with the suite green.
4. **Prove the generated project works for real.** For anything that changes generated
   output, create a project outside the repo and run it end to end:

   ```bash
   cd "$(mktemp -d)"
   uv run --project <path-to-this-repo> fastapi-foundry init demo
   cd demo && uv sync
   uv run uvicorn app.routes:app --port 8000 &   # then:
   curl http://127.0.0.1:8000/                   # {"message": "Hello from fastapi-foundry"}
   ```

   For migration changes, also run `fastapi-foundry migrate`, `migrate:status` and
   `migrate:rollback` against a database (`DATABASE_URL=sqlite:///./dev.sqlite` works).

When reporting work, show the failing run and the passing run, not only the final result.

### pytest setup

- Config in `pyproject.toml`: `testpaths = ["tests"]`, `--import-mode=importlib`. There are
  **no `__init__.py` or `conftest.py` files** in `tests/`; fixtures live in the file that uses
  them, and test file basenames must be unique across folders.
- Group tests inside a file with `# --- section ---` comments; module docstrings explain what
  the file covers and why it uses a given technique.
- Test names describe behaviour as a sentence: `test_existing_directory_is_not_overwritten`.
- Type-annotate tests and fixtures (`tmp_path: Path`, `-> None`).

### Techniques used in this suite

| Need | How |
|---|---|
| A project to work on | `create_project("myproject", parent_dir=tmp_path)` |
| Run a CLI command | `CliRunner().invoke(app, [...])` after `monkeypatch.chdir(...)`; assert `exit_code` and `output` |
| Interactive prompts | pass `input="2\nusers\n"` to `CliRunner().invoke` |
| Check generated Python structure | `ast.parse` the file (classes, imports, top-level names) and `compile()` every `.py` |
| Check generated config | `tomllib` for `pyproject.toml`, parse `.env` lines into a dict |
| Run generated code | `subprocess.run([sys.executable, "-c", script], cwd=project_root)` — keeps the generically named `app` package out of the test session's `sys.modules` and imports it exactly as uvicorn would |
| Serve a request | `fastapi.testclient.TestClient(app).get("/")` inside that subprocess |
| Run real migrations | run `python -m app.database.migrator <action>` in a subprocess with `DATABASE_URL=sqlite:///<tmp>/test.sqlite`; inspect with SQLAlchemy — no MySQL server needed |
| Deterministic migration names | `create_migration(..., now=datetime(2099, 1, 1, tzinfo=timezone.utc))` |
| Don't launch `uv` | `monkeypatch.setattr(runner.subprocess, "run", FakeRun())` and `runner.shutil.which` (see `tests/runner/test_migrate_command.py`) |
| Environment variables | `monkeypatch.setenv` / build an explicit `env` dict for the subprocess |

Always cover the unhappy paths too: invalid input is rejected, nothing is written or run
outside a project root, existing files are left untouched, and errors exit with code 1 and a
helpful message.

## Conventions

- Every module starts with a docstring stating its responsibility; public functions document
  the exceptions they raise in a `Raises:` section.
- Comments explain *why* (constraints, platform quirks), not what the code does.
- Type hints everywhere, using modern syntax (`str | None`, `list[str]`, `Annotated`).
- User-facing errors: `typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)` then
  `raise typer.Exit(code=1) from error`. Success messages in green.
- Release: bump `version` in `pyproject.toml` (commit message style: `Bump version to X.Y.Z`).
