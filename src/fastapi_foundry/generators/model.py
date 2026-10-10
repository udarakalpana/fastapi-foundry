"""Generate SQLAlchemy model classes for an existing project.

Models live in the project's ``app/model/`` directory, one snake_case module per
PascalCase class (``ProductModel`` in ``product_model.py``), all inheriting from
the ``Base`` in ``app/model/base.py``. The table a model maps is either one the
migrations already create or one derived from the model's name.
"""

import keyword
import re
from pathlib import Path

from fastapi_foundry.generators import templates
from fastapi_foundry.generators.migration import InvalidTableNameError, normalize_table_name

MODELS_DIR = Path("app", "model")
BASE_MODULE = "base.py"

# PascalCase: letters and digits only, starting with a capital letter. This also
# keeps the derived module name free of path separators and dots.
_VALID_MODEL_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")

# A trailing "Model" is a naming convention, not part of the table's name.
_MODEL_SUFFIX = "Model"

# "Base" is the declarative base class every model inherits from.
_RESERVED_MODEL_NAMES = frozenset({"Base"})

# Word boundaries in PascalCase: "OrderItem" -> "Order|Item", "HTTPClient" -> "HTTP|Client".
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

_EXAMPLE = "e.g. 'ProductModel' or 'OrderItemModel'"


class InvalidModelNameError(ValueError):
    """Raised when a model name cannot be used as a class and module name."""


class ModelExistsError(FileExistsError):
    """Raised when the model's file already exists."""


def normalize_model_name(raw_name: str) -> str:
    """Return ``raw_name`` as a valid PascalCase model name.

    Raises:
        InvalidModelNameError: if the name is not PascalCase, is reserved, or
            would not give a valid table name.
    """
    name = raw_name.strip()
    if not _VALID_MODEL_NAME.fullmatch(name):
        raise InvalidModelNameError(
            f"Invalid model name '{raw_name}'. Use PascalCase: letters and digits, "
            f"starting with a capital letter ({_EXAMPLE})."
        )
    if keyword.iskeyword(name) or name in _RESERVED_MODEL_NAMES or name == _MODEL_SUFFIX:
        raise InvalidModelNameError(
            f"Model name '{raw_name}' is reserved. Choose a more specific name ({_EXAMPLE})."
        )
    try:
        normalize_table_name(table_name_for_model(name))
    except InvalidTableNameError as error:
        raise InvalidModelNameError(
            f"Model name '{raw_name}' is too long to derive a table name from."
        ) from error
    return name


def model_module_name(model_name: str) -> str:
    """Return the snake_case module name for ``model_name`` (``ProductModel`` -> ``product_model``)."""
    return _snake_case(model_name)


def table_name_for_model(model_name: str) -> str:
    """Return the table a new model maps by default (``ProductModel`` -> ``products``)."""
    stem = model_name
    if stem.endswith(_MODEL_SUFFIX) and stem != _MODEL_SUFFIX:
        stem = stem.removesuffix(_MODEL_SUFFIX)
    *words, last = _snake_case(stem).split("_")
    return "_".join([*words, _pluralize(last)])


def model_name_for_table(table: str) -> str:
    """Return the suggested model name for ``table`` (``user_roles`` -> ``UserRoleModel``)."""
    *words, last = table.split("_")
    return "".join(word.capitalize() for word in [*words, _singularize(last)]) + _MODEL_SUFFIX


def models_dir(project_root: Path | None = None) -> Path:
    """Return the models directory for ``project_root``."""
    return (project_root or Path.cwd()) / MODELS_DIR


def create_model(model_name: str, table: str, project_root: Path | None = None) -> Path:
    """Create a model class mapping ``table`` and return the path to its module.

    ``app/model/base.py`` is written too if the project does not have it yet.

    Raises:
        InvalidModelNameError: if ``model_name`` is not a valid model name.
        InvalidTableNameError: if ``table`` is not a safe table name.
        ModelExistsError: if the model's module already exists.
    """
    class_name = normalize_model_name(model_name)
    table_name = normalize_table_name(table)

    directory = models_dir(project_root)
    directory.mkdir(parents=True, exist_ok=True)

    model_path = directory / f"{model_module_name(class_name)}.py"
    # "x" mode never overwrites a model the user may have edited.
    try:
        with model_path.open("x", encoding="utf-8") as file:
            file.write(templates.model_py(class_name, table_name))
    except FileExistsError as error:
        raise ModelExistsError(
            f"'{(MODELS_DIR / model_path.name).as_posix()}' already exists. "
            "Choose a different model name or remove the existing file."
        ) from error

    # Projects created before models existed have no base yet; an existing one,
    # possibly customised, is kept.
    try:
        with (directory / BASE_MODULE).open("x", encoding="utf-8") as file:
            file.write(templates.MODEL_BASE_PY)
    except FileExistsError:
        pass

    return model_path


def _snake_case(name: str) -> str:
    return _WORD_BOUNDARY.sub("_", name).lower()


def _pluralize(word: str) -> str:
    """English plural for the common cases; good enough for a default table name."""
    if len(word) > 1 and word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def _singularize(word: str) -> str:
    """Undo :func:`_pluralize` for the common cases, leaving other words alone."""
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("ss", "us", "x", "ch", "sh")):
        return word[:-2]
    if len(word) > 1 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word
