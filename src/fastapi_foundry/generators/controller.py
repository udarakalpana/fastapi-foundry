"""Generate controller classes for an existing project.

Controllers live in the project's ``app/controller/`` directory, one snake_case
module per PascalCase class (``ProductController`` in ``product_controller.py``).
Routes in ``app/routes.py`` stay the user's to write: the generator never edits
that file, it only returns a snippet showing how to wire the new controller in.
"""

import re
from pathlib import Path

from fastapi_foundry.generators import templates
from fastapi_foundry.generators.naming import pluralize, snake_case

CONTROLLERS_DIR = Path("app", "controller")

# PascalCase: letters and digits only, starting with a capital letter. This also
# keeps the derived module name free of path separators and dots.
_VALID_CONTROLLER_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")

_CONTROLLER_SUFFIX = "Controller"

# Keeps module names, and the route snippet's lines, a readable length.
_MAX_CONTROLLER_NAME_LENGTH = 64

_EXAMPLE = "e.g. 'ProductController' or 'OrderItemController'"


class InvalidControllerNameError(ValueError):
    """Raised when a controller name cannot be used as a class and module name."""


class ControllerExistsError(FileExistsError):
    """Raised when the controller's file already exists."""


def normalize_controller_name(raw_name: str) -> str:
    """Return ``raw_name`` as a valid PascalCase controller name ending in ``Controller``.

    A missing ``Controller`` suffix is added, so ``Product`` becomes ``ProductController``.

    Raises:
        InvalidControllerNameError: if the name is not PascalCase, is a bare
            ``Controller`` or is too long.
    """
    name = raw_name.strip()
    if not _VALID_CONTROLLER_NAME.fullmatch(name):
        raise InvalidControllerNameError(
            f"Invalid controller name '{raw_name}'. Use PascalCase: letters and digits, "
            f"starting with a capital letter ({_EXAMPLE})."
        )
    if name == _CONTROLLER_SUFFIX:
        raise InvalidControllerNameError(
            f"Controller name '{raw_name}' is reserved. Choose a more specific name ({_EXAMPLE})."
        )
    if not name.endswith(_CONTROLLER_SUFFIX):
        name += _CONTROLLER_SUFFIX
    if len(name) > _MAX_CONTROLLER_NAME_LENGTH:
        raise InvalidControllerNameError(
            f"Controller name '{raw_name}' is too long "
            f"(at most {_MAX_CONTROLLER_NAME_LENGTH} characters)."
        )
    # No keyword check is needed: PascalCase rules out all but True/False/None,
    # and those always gain the suffix.
    return name


def controller_module_name(controller_name: str) -> str:
    """Return the module name (``ProductController`` -> ``product_controller``)."""
    return snake_case(controller_name)


def route_path_for_controller(controller_name: str) -> str:
    """Return the suggested route path (``OrderItemController`` -> ``/order-items``)."""
    return "/" + "-".join(_resource_words(controller_name))


def route_function_name(controller_name: str) -> str:
    """Return the suggested route function (``OrderItemController`` -> ``list_order_items``)."""
    return "list_" + "_".join(_resource_words(controller_name))


def controllers_dir(project_root: Path | None = None) -> Path:
    """Return the controllers directory for ``project_root``."""
    return (project_root or Path.cwd()) / CONTROLLERS_DIR


def create_controller(controller_name: str, project_root: Path | None = None) -> Path:
    """Create a controller class and return the path to its module.

    Raises:
        InvalidControllerNameError: if ``controller_name`` is not a valid controller name.
        ControllerExistsError: if the controller's module already exists.
    """
    class_name = normalize_controller_name(controller_name)

    directory = controllers_dir(project_root)
    directory.mkdir(parents=True, exist_ok=True)

    controller_path = directory / f"{controller_module_name(class_name)}.py"
    # "x" mode never overwrites a controller the user may have edited.
    try:
        with controller_path.open("x", encoding="utf-8") as file:
            file.write(
                templates.controller_py(class_name, " ".join(_resource_words(class_name)))
            )
    except FileExistsError as error:
        raise ControllerExistsError(
            f"'{(CONTROLLERS_DIR / controller_path.name).as_posix()}' already exists. "
            "Choose a different controller name or remove the existing file."
        ) from error

    return controller_path


def route_snippet(controller_name: str) -> str:
    """Return the code to add to ``app/routes.py`` to serve the controller's ``index``.

    Raises:
        InvalidControllerNameError: if ``controller_name`` is not a valid controller name.
    """
    class_name = normalize_controller_name(controller_name)
    return templates.controller_route_py(
        class_name=class_name,
        module=controller_module_name(class_name),
        path=route_path_for_controller(class_name),
        function=route_function_name(class_name),
    )


def _resource_words(controller_name: str) -> list[str]:
    """The plural resource a controller handles (``OrderItemController`` -> order, items)."""
    *words, last = snake_case(controller_name.removesuffix(_CONTROLLER_SUFFIX)).split("_")
    return [*words, pluralize(last)]
