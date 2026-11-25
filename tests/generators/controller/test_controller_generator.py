"""Tests for the files ``create_controller`` writes into a project's app/controller/.

The generated code is inspected with ``ast`` (class and methods) and compiled;
serving a request through it is covered in test_controller_runs.py.
"""

import ast
from pathlib import Path

import pytest

from fastapi_foundry.generators.controller import (
    CONTROLLERS_DIR,
    ControllerExistsError,
    InvalidControllerNameError,
    create_controller,
    route_snippet,
)


def _class_def(path: Path, name: str) -> ast.ClassDef:
    module = ast.parse(path.read_text(encoding="utf-8"))
    (class_def,) = (
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == name
    )
    return class_def


# --- file locations -------------------------------------------------------


def test_controller_is_written_to_the_controllers_directory(tmp_path: Path) -> None:
    controller_path = create_controller("ProductController", tmp_path)

    assert controller_path == tmp_path / CONTROLLERS_DIR / "product_controller.py"
    assert controller_path.is_file()


def test_controllers_directory_is_app_controller() -> None:
    assert CONTROLLERS_DIR == Path("app", "controller")


def test_name_without_suffix_gets_a_controller_module(tmp_path: Path) -> None:
    controller_path = create_controller("Product", tmp_path)

    assert controller_path.name == "product_controller.py"
    _class_def(controller_path, "ProductController")


# --- generated content ----------------------------------------------------


def test_controller_class_has_an_index_method(tmp_path: Path) -> None:
    controller_path = create_controller("ProductController", tmp_path)

    class_def = _class_def(controller_path, "ProductController")
    methods = [node.name for node in class_def.body if isinstance(node, ast.FunctionDef)]
    assert methods == ["index"]
    assert class_def.bases == []


def test_controller_module_and_class_have_docstrings(tmp_path: Path) -> None:
    controller_path = create_controller("OrderItemController", tmp_path)

    module = ast.parse(controller_path.read_text())
    class_def = _class_def(controller_path, "OrderItemController")
    assert "order items" in (ast.get_docstring(module) or "")
    assert "order items" in (ast.get_docstring(class_def) or "")


def test_generated_controller_compiles(tmp_path: Path) -> None:
    controller_path = create_controller("ProductController", tmp_path)

    compile(controller_path.read_text(encoding="utf-8"), str(controller_path), "exec")


def test_route_snippet_imports_and_uses_the_controller() -> None:
    snippet = route_snippet("ProductController")

    assert "from app.controller.product_controller import ProductController" in snippet
    assert "product_controller = ProductController()" in snippet
    assert '@app.get("/products")' in snippet
    assert "def list_products() -> dict[str, str]:" in snippet
    assert "return product_controller.index()" in snippet
    compile(snippet, "<snippet>", "exec")


# --- unhappy paths --------------------------------------------------------


def test_existing_controller_file_is_not_overwritten(tmp_path: Path) -> None:
    controller_path = create_controller("ProductController", tmp_path)
    controller_path.write_text("# edited by hand\n")

    with pytest.raises(ControllerExistsError, match="product_controller.py"):
        create_controller("ProductController", tmp_path)

    assert controller_path.read_text() == "# edited by hand\n"


def test_invalid_controller_name_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(InvalidControllerNameError):
        create_controller("../evil", tmp_path)

    assert not (tmp_path / "app").exists()
