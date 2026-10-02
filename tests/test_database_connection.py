"""Tests for the SQLAlchemy connection that ``init`` writes to app/config/sqlalchemy_connection.py."""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fastapi_foundry.generators.project import create_project


def _top_level_names(python_file: Path) -> set[str]:
    """Return the names a module defines at top level (assignments and functions)."""
    module = ast.parse(python_file.read_text())
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _run_in_project(
    project_root: Path, script: str, database_url: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` from the project root, as uvicorn would import the app.

    A subprocess keeps the generically named ``app`` package out of this test
    session's sys.modules. ``DATABASE_URL`` is only set when given, so the
    generated default is what gets tested otherwise.
    """
    env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
    if database_url is not None:
        env["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )


# --- generated source -----------------------------------------------------


def test_connection_module_defines_engine_session_factory_and_get_db(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    names = _top_level_names(project_root / "app" / "config" / "sqlalchemy_connection.py")

    assert {"engine", "SessionLocal", "get_db"} <= names


def test_config_defines_database_url(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert "DATABASE_URL" in _top_level_names(project_root / "app" / "config" / "database.py")


@pytest.mark.parametrize(
    ("project", "database"),
    [("myproject", "myproject"), ("my-fastapi-app", "my_fastapi_app")],
)
def test_env_file_defines_a_mysql_database_url(
    tmp_path: Path, project: str, database: str
) -> None:
    project_root = create_project(project, parent_dir=tmp_path)

    env_lines = (project_root / ".env").read_text().splitlines()
    values = dict(line.split("=", 1) for line in env_lines if "=" in line)

    assert values["DATABASE_URL"].startswith("mysql+pymysql://")
    assert values["DATABASE_URL"].endswith(f"/{database}")


def test_generated_readme_documents_database_url(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert "DATABASE_URL" in (project_root / "README.md").read_text()


# --- the generated connection actually works ------------------------------


@pytest.mark.parametrize(
    ("project", "database"),
    [("myproject", "myproject"), ("my-fastapi-app", "my_fastapi_app")],
)
def test_default_engine_targets_mysql_without_connecting(
    tmp_path: Path, project: str, database: str
) -> None:
    project_root = create_project(project, parent_dir=tmp_path)

    # No MySQL server runs here, so this also proves that importing the module
    # (and so starting the app) does not open a connection.
    script = (
        "from app.config.sqlalchemy_connection import engine\n"
        "print(engine.url.drivername)\n"
        "print(engine.url.database)\n"
    )
    result = _run_in_project(project_root, script)

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["mysql+pymysql", database]


def test_engine_uses_database_url_from_the_environment(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)
    database_url = f"sqlite:///{tmp_path / 'override.db'}"

    script = (
        "from app.config.sqlalchemy_connection import engine\n"
        "print(engine.url.render_as_string(hide_password=False))\n"
    )
    result = _run_in_project(project_root, script, database_url=database_url)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == database_url


def test_get_db_yields_a_working_session_and_closes_it(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    script = (
        "from sqlalchemy import text\n"
        "from sqlalchemy.orm import Session\n"
        "from app.config.sqlalchemy_connection import get_db\n"
        "dependency = get_db()\n"
        "session = next(dependency)\n"
        "assert isinstance(session, Session), type(session)\n"
        "print(session.execute(text('SELECT 1')).scalar_one())\n"
        "assert session.in_transaction()\n"
        # FastAPI finishes the generator after the response is sent.
        "assert next(dependency, 'finished') == 'finished'\n"
        "assert not session.in_transaction(), 'session was not closed'\n"
        "print('closed')\n"
    )
    result = _run_in_project(
        project_root, script, database_url=f"sqlite:///{tmp_path / 'app.db'}"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["1", "closed"]


def test_get_db_works_as_a_fastapi_dependency(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    script = (
        "from typing import Annotated\n"
        "from fastapi import Depends\n"
        "from fastapi.testclient import TestClient\n"
        "from sqlalchemy import text\n"
        "from sqlalchemy.orm import Session\n"
        "from app.config.sqlalchemy_connection import get_db\n"
        "from app.routes import app\n"
        "@app.get('/db-check')\n"
        "def db_check(db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:\n"
        "    return {'result': db.execute(text('SELECT 1')).scalar_one()}\n"
        "response = TestClient(app).get('/db-check')\n"
        "assert response.status_code == 200, response.text\n"
        "print(response.json()['result'])\n"
    )
    result = _run_in_project(
        project_root, script, database_url=f"sqlite:///{tmp_path / 'app.db'}"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"
