"""Tests for the files ``create_model`` writes into a project's app/model/.

The generated code is inspected with ``ast`` (class, base class, table name)
and compiled; running it against a database is covered in test_model_runs.py.
"""

import ast
from pathlib import Path

import pytest

from fastapi_foundry.generators.migration import InvalidTableNameError
from fastapi_foundry.generators.model import (
    MODELS_DIR,
    InvalidModelNameError,
    ModelExistsError,
    create_model,
)


def _class_def(path: Path, name: str) -> ast.ClassDef:
    module = ast.parse(path.read_text(encoding="utf-8"))
    (class_def,) = (
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == name
    )
    return class_def


def _tablename(class_def: ast.ClassDef) -> str:
    for node in class_def.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in node.targets)
            and isinstance(node.value, ast.Constant)
        ):
            return node.value.value
    raise AssertionError("no __tablename__ in class")


def _annotated_names(class_def: ast.ClassDef) -> list[str]:
    return [
        node.target.id
        for node in class_def.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]


# --- file locations -------------------------------------------------------


def test_model_is_written_to_the_models_directory(tmp_path: Path) -> None:
    model_path = create_model("ProductModel", "products", tmp_path)

    assert model_path == tmp_path / MODELS_DIR / "product_model.py"
    assert model_path.is_file()


def test_models_directory_is_app_model() -> None:
    assert MODELS_DIR == Path("app", "model")


def test_base_module_is_created_when_missing(tmp_path: Path) -> None:
    create_model("ProductModel", "products", tmp_path)

    base_path = tmp_path / MODELS_DIR / "base.py"
    assert base_path.is_file()
    base_class = _class_def(base_path, "Base")
    assert [ast.unparse(base) for base in base_class.bases] == ["DeclarativeBase"]


def test_existing_base_module_is_not_overwritten(tmp_path: Path) -> None:
    base_path = tmp_path / MODELS_DIR / "base.py"
    base_path.parent.mkdir(parents=True)
    base_path.write_text("# my own base\n")

    create_model("ProductModel", "products", tmp_path)

    assert base_path.read_text() == "# my own base\n"


def test_second_model_reuses_the_base_module(tmp_path: Path) -> None:
    create_model("ProductModel", "products", tmp_path)
    base_before = (tmp_path / MODELS_DIR / "base.py").read_text()

    create_model("UserModel", "users", tmp_path)

    assert (tmp_path / MODELS_DIR / "base.py").read_text() == base_before
    assert (tmp_path / MODELS_DIR / "user_model.py").is_file()


# --- generated content ----------------------------------------------------


def test_model_class_inherits_from_base(tmp_path: Path) -> None:
    model_path = create_model("ProductModel", "products", tmp_path)

    class_def = _class_def(model_path, "ProductModel")
    assert [ast.unparse(base) for base in class_def.bases] == ["Base"]
    assert "from app.model.base import Base" in model_path.read_text()


def test_model_maps_the_given_table(tmp_path: Path) -> None:
    model_path = create_model("UserModel", "users", tmp_path)

    assert _tablename(_class_def(model_path, "UserModel")) == "users"


def test_table_name_is_normalized(tmp_path: Path) -> None:
    model_path = create_model("UserModel", "  Users ", tmp_path)

    assert _tablename(_class_def(model_path, "UserModel")) == "users"


def test_model_has_the_default_migration_columns(tmp_path: Path) -> None:
    model_path = create_model("UserModel", "users", tmp_path)

    columns = _annotated_names(_class_def(model_path, "UserModel"))
    assert columns == ["id", "created_at", "updated_at"]


def test_every_generated_file_compiles(tmp_path: Path) -> None:
    create_model("ProductModel", "products", tmp_path)

    for path in (tmp_path / MODELS_DIR).glob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_model_module_has_a_docstring(tmp_path: Path) -> None:
    model_path = create_model("ProductModel", "products", tmp_path)

    docstring = ast.get_docstring(ast.parse(model_path.read_text()))
    assert docstring is not None and "products" in docstring


# --- unhappy paths --------------------------------------------------------


def test_existing_model_file_is_not_overwritten(tmp_path: Path) -> None:
    model_path = create_model("ProductModel", "products", tmp_path)
    model_path.write_text("# edited by hand\n")

    with pytest.raises(ModelExistsError, match="product_model.py"):
        create_model("ProductModel", "products", tmp_path)

    assert model_path.read_text() == "# edited by hand\n"


def test_invalid_model_name_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(InvalidModelNameError):
        create_model("../evil", "products", tmp_path)

    assert not (tmp_path / "app").exists()


def test_invalid_table_name_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(InvalidTableNameError):
        create_model("ProductModel", "products; drop", tmp_path)

    assert not (tmp_path / "app").exists()
