"""Tests for the ``DB_*`` settings that ``init`` writes to .env and app/config/database.py.

Each part of the connection (driver, host, port, database, username, password)
is its own environment variable, and ``app/config/database.py`` builds
``DATABASE_URL`` from them.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fastapi_foundry.generators.project import create_project

DB_SETTINGS = [
    "DB_CONNECTION",
    "DB_HOST",
    "DB_PORT",
    "DB_DATABASE",
    "DB_USERNAME",
    "DB_PASSWORD",
]


def _top_level_names(python_file: Path) -> set[str]:
    """Return the names a module assigns at top level."""
    module = ast.parse(python_file.read_text())
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _env_values(project_root: Path) -> dict[str, str]:
    env_lines = (project_root / ".env").read_text().splitlines()
    return dict(line.split("=", 1) for line in env_lines if "=" in line)


def _engine_url(project_root: Path, **settings: str) -> subprocess.CompletedProcess[str]:
    """Print the generated engine's URL parts with only ``settings`` in the environment.

    A subprocess keeps the generically named ``app`` package out of this test
    session's sys.modules, and any database variables of the machine running
    the tests are removed so the generated defaults are what gets tested.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {*DB_SETTINGS, "DATABASE_URL"}
    }
    env.update(settings)
    script = (
        "from app.config.sqlalchemy_connection import engine\n"
        "url = engine.url\n"
        "for part in (url.drivername, url.host, url.port, url.database,"
        " url.username, url.password):\n"
        "    print(repr(part))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )


def _url_parts(result: subprocess.CompletedProcess[str]) -> list[object]:
    assert result.returncode == 0, result.stderr
    return [ast.literal_eval(line) for line in result.stdout.splitlines()]


# --- generated files ------------------------------------------------------


@pytest.mark.parametrize(
    ("project", "database"),
    [("myproject", "myproject"), ("my-fastapi-app", "my_fastapi_app")],
)
def test_env_file_defines_each_connection_setting(
    tmp_path: Path, project: str, database: str
) -> None:
    project_root = create_project(project, parent_dir=tmp_path)

    values = _env_values(project_root)

    assert {name: values.get(name) for name in DB_SETTINGS} == {
        "DB_CONNECTION": "mysql+pymysql",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_DATABASE": database,
        "DB_USERNAME": "root",
        "DB_PASSWORD": "",
    }


def test_env_file_does_not_set_a_database_url(tmp_path: Path) -> None:
    """A DATABASE_URL in .env would override the DB_* settings next to it."""
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert "DATABASE_URL" not in _env_values(project_root)


def test_database_config_defines_each_setting_and_the_url(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    names = _top_level_names(project_root / "app" / "config" / "database.py")

    assert names == {*DB_SETTINGS, "DATABASE_URL"}


def test_generated_readme_documents_each_setting(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    readme = (project_root / "README.md").read_text()

    assert all(name in readme for name in DB_SETTINGS)


# --- the settings reach the engine ----------------------------------------


@pytest.mark.parametrize(
    ("project", "database"),
    [("myproject", "myproject"), ("my-fastapi-app", "my_fastapi_app")],
)
def test_defaults_match_the_env_file(tmp_path: Path, project: str, database: str) -> None:
    project_root = create_project(project, parent_dir=tmp_path)

    parts = _url_parts(_engine_url(project_root))

    assert parts == ["mysql+pymysql", "127.0.0.1", 3306, database, "root", ""]


@pytest.mark.parametrize(
    ("setting", "value", "index", "expected"),
    [
        ("DB_CONNECTION", "mariadb+pymysql", 0, "mariadb+pymysql"),
        ("DB_HOST", "db.internal", 1, "db.internal"),
        ("DB_PORT", "3307", 2, 3307),
        ("DB_DATABASE", "shop", 3, "shop"),
        ("DB_USERNAME", "app_user", 4, "app_user"),
        ("DB_PASSWORD", "secret", 5, "secret"),
    ],
)
def test_each_setting_is_used_in_the_url(
    tmp_path: Path, setting: str, value: str, index: int, expected: object
) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    parts = _url_parts(_engine_url(project_root, **{setting: value}))

    assert parts[index] == expected


def test_special_characters_in_credentials_are_escaped(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    parts = _url_parts(
        _engine_url(project_root, DB_USERNAME="admin@corp", DB_PASSWORD="p@ss:w/rd#%")
    )

    assert parts[1:] == ["127.0.0.1", 3306, "myproject", "admin@corp", "p@ss:w/rd#%"]


def test_database_url_overrides_the_db_settings(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    database_url = f"sqlite:///{tmp_path / 'override.db'}"

    parts = _url_parts(
        _engine_url(project_root, DATABASE_URL=database_url, DB_HOST="ignored.example")
    )

    assert parts[0] == "sqlite"
    assert parts[3] == str(tmp_path / "override.db")


def test_settings_load_from_the_env_file(tmp_path: Path) -> None:
    """``uvicorn --env-file .env`` loads the file with python-dotenv before importing the app."""
    project_root = create_project("myproject", parent_dir=tmp_path)
    env_file = project_root / ".env"
    env_file.write_text(
        env_file.read_text()
        .replace("DB_HOST=127.0.0.1", "DB_HOST=db.example.com")
        .replace("DB_PASSWORD=", "DB_PASSWORD=from-env-file")
    )

    script = (
        "from dotenv import load_dotenv\n"
        "load_dotenv('.env')\n"
        "from app.config.sqlalchemy_connection import engine\n"
        "print(engine.url.host, engine.url.password)\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {*DB_SETTINGS, "DATABASE_URL"}
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["db.example.com", "from-env-file"]
