"""Tests for the interactive ``fastapi-foundry controller`` command.

The command is driven through ``CliRunner`` with scripted answers, against a
project created in ``tmp_path``.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from fastapi_foundry.cli import app
from fastapi_foundry.generators.controller import CONTROLLERS_DIR
from fastapi_foundry.generators.project import create_project
from fastapi_foundry.generators.templates import ROUTES_PY


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = create_project("myproject", parent_dir=tmp_path)
    monkeypatch.chdir(project_root)
    return project_root


def _invoke(answers: str) -> Result:
    return CliRunner().invoke(app, ["controller"], input=answers)


# --- creating a controller ------------------------------------------------


def test_controller_is_created_from_the_given_name(project: Path) -> None:
    result = _invoke("ProductController\n")

    assert result.exit_code == 0, result.output
    controller_path = project / CONTROLLERS_DIR / "product_controller.py"
    assert "class ProductController:" in controller_path.read_text()
    assert "Created controller: app/controller/product_controller.py" in result.output


def test_prompt_shows_an_example_name(project: Path) -> None:
    result = _invoke("ProductController\n")

    assert "Controller name (PascalCase, e.g. ProductController)" in result.output


def test_name_without_suffix_creates_a_suffixed_controller(project: Path) -> None:
    result = _invoke("Product\n")

    assert result.exit_code == 0, result.output
    assert (project / CONTROLLERS_DIR / "product_controller.py").is_file()


def test_output_shows_how_to_add_a_route(project: Path) -> None:
    result = _invoke("ProductController\n")

    assert "app/routes.py" in result.output
    assert "from app.controller.product_controller import ProductController" in result.output
    assert '@app.get("/products")' in result.output


def test_routes_file_is_left_untouched(project: Path) -> None:
    _invoke("ProductController\n")

    assert (project / "app" / "routes.py").read_text() == ROUTES_PY


def test_invalid_controller_name_is_asked_again(project: Path) -> None:
    result = _invoke("product_controller\nProductController\n")

    assert result.exit_code == 0, result.output
    assert "Error:" in result.output
    assert (project / CONTROLLERS_DIR / "product_controller.py").is_file()


# --- unhappy paths --------------------------------------------------------


def test_existing_controller_is_not_overwritten(project: Path) -> None:
    home_path = project / CONTROLLERS_DIR / "home_controller.py"
    home_before = home_path.read_text()

    result = _invoke("HomeController\n")

    assert result.exit_code == 1
    assert "Error:" in result.output and "already exists" in result.output
    assert home_path.read_text() == home_before


def test_outside_a_project_nothing_is_asked_or_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = _invoke("ProductController\n")

    assert result.exit_code == 1
    assert "not a fastapi-foundry project" in result.output
    assert "Controller name" not in result.output
    assert list(tmp_path.iterdir()) == []
