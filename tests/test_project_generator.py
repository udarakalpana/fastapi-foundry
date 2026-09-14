import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry.cli import app
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
    "src/{package}/__init__.py",
    "src/{package}/main.py",
    "src/{package}/config.py",
    "src/{package}/database/__init__.py",
    "src/{package}/database/connection.py",
]


def test_create_project_generates_expected_structure(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    assert project_root == tmp_path / "myproject"
    for relative_path in EXPECTED_FILES:
        assert (project_root / relative_path.format(package="myproject")).is_file()


def test_generated_pyproject_is_valid(tmp_path: Path) -> None:
    project_root = create_project("my-fastapi-app", parent_dir=tmp_path)

    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "my-fastapi-app"
    dependencies = pyproject["project"]["dependencies"]
    assert any(dep.startswith("fastapi") for dep in dependencies)
    assert any(dep.startswith("uvicorn") for dep in dependencies)
    assert pyproject["tool"]["uv"]["build-backend"]["module-name"] == "my_fastapi_app"


def test_generated_python_files_compile(tmp_path: Path) -> None:
    project_root = create_project("myproject", parent_dir=tmp_path)

    for python_file in project_root.rglob("*.py"):
        compile(python_file.read_text(), str(python_file), "exec")


def test_hyphenated_name_is_normalized_to_package_name(tmp_path: Path) -> None:
    project_root = create_project("my-fastapi-app", parent_dir=tmp_path)

    assert project_root.name == "my-fastapi-app"
    assert (project_root / "src" / "my_fastapi_app" / "main.py").is_file()


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


def test_cli_init_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["init", "myproject"])

    assert result.exit_code == 0, result.output
    assert "Created FastAPI project: myproject" in result.output
    assert (tmp_path / "myproject" / "src" / "myproject" / "main.py").is_file()


def test_cli_init_fails_for_existing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "myproject").mkdir()

    result = CliRunner().invoke(app, ["init", "myproject"])

    assert result.exit_code == 1
    assert "already exists" in result.output
