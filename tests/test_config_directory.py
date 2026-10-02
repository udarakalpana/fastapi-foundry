"""Tests for the ``app/config/`` directory that ``init`` writes.

Each kind of configuration has its own module, and the SQLAlchemy connection
lives next to the database settings it is built from.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fastapi_foundry.generators.project import create_project

CONFIG_FILES = ["app.py", "database.py", "sqlalchemy_connection.py"]


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


def _imports_from(python_file: Path) -> dict[str, set[str]]:
    """Map each ``from X import ...`` module to the names imported from it."""
    module = ast.parse(python_file.read_text())
    imports: dict[str, set[str]] = {}
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.setdefault(node.module, set()).update(a.name for a in node.names)
    return imports


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return create_project("myproject", parent_dir=tmp_path) / "app" / "config"


# --- layout ---------------------------------------------------------------


def test_config_directory_holds_one_module_per_configuration(config_dir: Path) -> None:
    assert sorted(p.name for p in config_dir.iterdir()) == CONFIG_FILES


def test_old_config_and_connection_modules_are_not_generated(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert not (project_root / "app" / "config.py").exists()
    assert not (project_root / "app" / "database" / "connection.py").exists()


# --- each module owns its own settings ------------------------------------


def test_database_config_holds_only_database_settings(config_dir: Path) -> None:
    assert _top_level_names(config_dir / "database.py") == {"DATABASE_URL"}


def test_app_config_holds_only_application_settings(config_dir: Path) -> None:
    assert _top_level_names(config_dir / "app.py") == {"APP_NAME", "DEBUG"}


def test_connection_reads_the_url_from_the_database_config(config_dir: Path) -> None:
    imports = _imports_from(config_dir / "sqlalchemy_connection.py")

    assert "DATABASE_URL" in imports.get("app.config.database", set())


def test_routes_read_settings_from_the_app_config(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    imports = _imports_from(project_root / "app" / "routes.py")

    assert {"APP_NAME", "DEBUG"} <= imports.get("app.config.app", set())


# --- the modules import from the project root -----------------------------


def test_config_modules_import_without_a_database(tmp_path: Path) -> None:
    project_root = create_project("my-fastapi-app", parent_dir=tmp_path)

    script = (
        "from app.config.app import APP_NAME, DEBUG\n"
        "from app.config.database import DATABASE_URL\n"
        "from app.config.sqlalchemy_connection import engine, get_db\n"
        "print(APP_NAME, DEBUG)\n"
        "print(DATABASE_URL)\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in {"APP_NAME", "DEBUG", "DATABASE_URL"}}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    app_line, url_line = result.stdout.splitlines()
    assert app_line == "my-fastapi-app False"
    assert url_line == "mysql+pymysql://root:@127.0.0.1:3306/my_fastapi_app"
