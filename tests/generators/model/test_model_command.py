"""Tests for the interactive ``fastapi-foundry model`` command.

The command is driven through ``CliRunner`` with scripted answers, against a
project created in ``tmp_path``.
"""

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from fastapi_foundry.cli import app
from fastapi_foundry.generators.migration import MIGRATIONS_DIR
from fastapi_foundry.generators.model import MODELS_DIR
from fastapi_foundry.generators.project import create_project

# Answers to "Is this model for an existing database table?"
YES = "1\n"
NO = "2\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = create_project("myproject", parent_dir=tmp_path)
    monkeypatch.chdir(project_root)
    return project_root


def _invoke(answers: str) -> Result:
    return CliRunner().invoke(app, ["model"], input=answers)


def _tablename(path: Path) -> str:
    for node in ast.walk(ast.parse(path.read_text())):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in node.targets)
            and isinstance(node.value, ast.Constant)
        ):
            return node.value.value
    raise AssertionError("no __tablename__")


# --- existing table -------------------------------------------------------


def test_existing_table_with_the_default_model_name(project: Path) -> None:
    # "users" is the only table, then Enter accepts the suggested name.
    result = _invoke(YES + "1\n\n")

    assert result.exit_code == 0, result.output
    model_path = project / MODELS_DIR / "user_model.py"
    assert model_path.is_file()
    assert _tablename(model_path) == "users"
    assert "class UserModel(Base)" in model_path.read_text()
    assert "Created model: app/model/user_model.py" in result.output


def test_existing_table_lists_the_tables_and_suggests_a_name(project: Path) -> None:
    result = _invoke(YES + "1\n\n")

    assert "Is this model for an existing database table?" in result.output
    assert "1) Yes" in result.output and "2) No" in result.output
    assert "1) users" in result.output
    assert "[UserModel]" in result.output


def test_existing_table_with_a_custom_model_name(project: Path) -> None:
    result = _invoke(YES + "1\nMemberModel\n")

    assert result.exit_code == 0, result.output
    model_path = project / MODELS_DIR / "member_model.py"
    assert _tablename(model_path) == "users"
    assert not (project / MODELS_DIR / "user_model.py").exists()


def test_existing_table_without_any_tables_exits_with_an_error(project: Path) -> None:
    for migration_file in (project / MIGRATIONS_DIR).glob("*_users_table.py"):
        migration_file.unlink()

    result = _invoke(YES)

    assert result.exit_code == 1
    assert "No existing tables" in result.output
    assert not (project / MODELS_DIR).exists()


# --- new model ------------------------------------------------------------


def test_new_model_derives_its_table_from_the_name(project: Path) -> None:
    result = _invoke(NO + "ProductModel\n")

    assert result.exit_code == 0, result.output
    model_path = project / MODELS_DIR / "product_model.py"
    assert _tablename(model_path) == "products"
    assert "Created model: app/model/product_model.py" in result.output


def test_new_model_prompt_shows_an_example_name(project: Path) -> None:
    result = _invoke(NO + "ProductModel\n")

    assert "e.g. ProductModel" in result.output


def test_invalid_model_name_is_asked_again(project: Path) -> None:
    result = _invoke(NO + "product_model\nProductModel\n")

    assert result.exit_code == 0, result.output
    assert "Error:" in result.output
    assert (project / MODELS_DIR / "product_model.py").is_file()


# --- unhappy paths --------------------------------------------------------


def test_existing_model_is_not_overwritten(project: Path) -> None:
    assert _invoke(NO + "ProductModel\n").exit_code == 0
    model_path = project / MODELS_DIR / "product_model.py"
    model_path.write_text("# edited by hand\n")

    result = _invoke(NO + "ProductModel\n")

    assert result.exit_code == 1
    assert "Error:" in result.output and "already exists" in result.output
    assert model_path.read_text() == "# edited by hand\n"


def test_outside_a_project_nothing_is_asked_or_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = _invoke(NO + "ProductModel\n")

    assert result.exit_code == 1
    assert "not a fastapi-foundry project" in result.output
    assert "existing database table" not in result.output
    assert list(tmp_path.iterdir()) == []
