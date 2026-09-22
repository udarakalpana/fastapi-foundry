import ast
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry.cli import app
from fastapi_foundry.generators.migration import existing_tables
from fastapi_foundry.generators.project import (
    InvalidProjectNameError,
    ProjectExistsError,
    ProjectName,
    create_project,
)

EXPECTED_FILES = [
    "pyproject.toml",
    ".env",
    ".gitignore",
    "README.md",
    "app/config.py",
    "app/routes.py",
    "app/controller/home_controller.py",
    "app/database/connection.py",
]


# --- structure ------------------------------------------------------------


def test_create_project_generates_expected_structure(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert project_root == tmp_path / "myproject"
    for relative_path in EXPECTED_FILES:
        assert (project_root / relative_path).is_file()


def test_generated_project_is_a_flat_app_not_a_package(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert not (project_root / "src").exists()
    assert not (project_root / "app" / "myproject").exists()
    assert not (project_root / "app" / "main.py").exists()
    assert list(project_root.rglob("__init__.py")) == []


def test_hyphenated_name_keeps_the_folder_and_uses_a_flat_app_dir(tmp_path: Path) -> None:
    project_root = create_project("my-fastapi-app", parent_dir=tmp_path)

    assert project_root.name == "my-fastapi-app"
    assert (project_root / "app" / "routes.py").is_file()
    assert not (project_root / "app" / "my_fastapi_app").exists()


def test_existing_directory_is_not_overwritten(tmp_path: Path) -> None:
    existing_file = tmp_path / "myproject" / "README.md"
    existing_file.parent.mkdir()
    existing_file.write_text("keep me")

    with pytest.raises(ProjectExistsError):
        create_project("myproject", parent_dir=tmp_path)

    assert existing_file.read_text() == "keep me"
    assert list(existing_file.parent.iterdir()) == [existing_file]


@pytest.mark.parametrize(
    "invalid_name",
    ["", "../evil", "/tmp/evil", "a/b", ".hidden", "1project", "my project", "class", "json", "fastapi"],
)
def test_invalid_names_are_rejected(invalid_name: str) -> None:
    with pytest.raises(InvalidProjectNameError):
        ProjectName.from_raw(invalid_name)


# --- pyproject.toml -------------------------------------------------------


def test_generated_pyproject_is_valid(tmp_path: Path) -> None:
    project_root = create_project("my-fastapi-app", parent_dir=tmp_path)

    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "my-fastapi-app"
    dependencies = pyproject["project"]["dependencies"]
    for expected in ("fastapi", "uvicorn", "sqlalchemy", "pymysql"):
        assert any(dep.startswith(expected) for dep in dependencies), expected


def test_generated_project_is_not_built_as_a_package(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())

    # An application is deployed, not installed, so there is nothing to build.
    assert "build-system" not in pyproject
    assert pyproject["tool"]["uv"]["package"] is False


# --- generated python -----------------------------------------------------


def test_generated_python_files_compile(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    for python_file in project_root.rglob("*.py"):
        compile(python_file.read_text(), str(python_file), "exec")


def test_controller_defines_the_home_controller_class(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    module = ast.parse((project_root / "app" / "controller" / "home_controller.py").read_text())

    classes = {node.name for node in module.body if isinstance(node, ast.ClassDef)}
    assert "HomeController" in classes


def test_default_route_delegates_to_the_controller(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    module = ast.parse((project_root / "app" / "routes.py").read_text())

    imported = {
        alias.name
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "HomeController" in imported

    root_handler = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "root"
    )
    returned = root_handler.body[-1]
    # The route must call the controller, not return a literal of its own.
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert isinstance(returned.value.func, ast.Attribute)
    assert returned.value.func.attr == "index"


# --- default migration ----------------------------------------------------


def test_default_users_migration_is_generated(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    migrations = list((project_root / "app" / "database").glob("*_create_users_table.py"))
    assert len(migrations) == 1


def test_default_migration_is_discoverable_by_the_migration_command(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    # connection.py shares the directory and must not confuse the scanner.
    assert existing_tables(project_root) == ["users"]


# --- CLI ------------------------------------------------------------------


def test_cli_init_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["init", "myproject"])

    assert result.exit_code == 0, result.output
    assert "Created FastAPI project: myproject" in result.output
    assert "uvicorn app.routes:app" in result.output
    assert (tmp_path / "myproject" / "app" / "routes.py").is_file()


def test_cli_init_fails_for_existing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "myproject").mkdir()

    result = CliRunner().invoke(app, ["init", "myproject"])

    assert result.exit_code == 1
    assert "already exists" in result.output


# --- the generated app actually runs --------------------------------------


def test_generated_app_boots_and_serves_the_default_route(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    # A subprocess keeps a module as generically named as "app" out of this
    # test session's sys.modules, and proves the app is importable from the
    # project root exactly as uvicorn imports it.
    script = (
        "from fastapi.testclient import TestClient\n"
        "from app.routes import app\n"
        "response = TestClient(app).get('/')\n"
        "assert response.status_code == 200, response.status_code\n"
        "print(app.title)\n"
        "print(response.json()['message'])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "myproject" in result.stdout
    assert "Hello from fastapi-foundry" in result.stdout
