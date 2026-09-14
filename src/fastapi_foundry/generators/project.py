"""Generate a new FastAPI project on the filesystem."""

import keyword
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi_foundry.generators import templates

# Letters, digits, hyphens and underscores only, starting with a letter.
# This rules out path separators, "..", absolute paths and hidden directories.
_VALID_PROJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

# Package names that would shadow the generated project's own dependencies.
_RESERVED_PACKAGE_NAMES = frozenset(
    {"fastapi", "uvicorn", "starlette", "pydantic", "anyio", "src", "tests"}
)


class InvalidProjectNameError(ValueError):
    """Raised when a project name cannot be used safely."""


class ProjectExistsError(FileExistsError):
    """Raised when the target project directory already exists."""


@dataclass(frozen=True)
class ProjectName:
    """The different forms of a project name used during generation.

    For ``my-fastapi-app``:
        directory    -> ``my-fastapi-app``  (project root folder)
        distribution -> ``my-fastapi-app``  (``[project].name`` in pyproject.toml)
        package      -> ``my_fastapi_app``  (importable Python package)
    """

    directory: str
    distribution: str
    package: str

    @classmethod
    def from_raw(cls, raw_name: str) -> "ProjectName":
        name = raw_name.strip()
        if not _VALID_PROJECT_NAME.fullmatch(name):
            raise InvalidProjectNameError(
                f"Invalid project name '{raw_name}'. Use letters, digits, '-' or '_', "
                "starting with a letter (e.g. 'myproject' or 'my-fastapi-app')."
            )

        package = name.lower().replace("-", "_")
        if keyword.iskeyword(package):
            raise InvalidProjectNameError(
                f"Project name '{raw_name}' is a Python keyword."
            )
        if package in sys.stdlib_module_names or package in _RESERVED_PACKAGE_NAMES:
            raise InvalidProjectNameError(
                f"Project name '{raw_name}' would shadow the '{package}' module. "
                "Choose a different name."
            )

        return cls(
            directory=name,
            distribution=package.replace("_", "-"),
            package=package,
        )


def create_project(name: str | ProjectName, parent_dir: Path | None = None) -> Path:
    """Create a new FastAPI project and return the path to its root directory.

    Raises:
        InvalidProjectNameError: if ``name`` is not a safe project name.
        ProjectExistsError: if the project directory already exists.
    """
    project_name = name if isinstance(name, ProjectName) else ProjectName.from_raw(name)
    project_root = (parent_dir or Path.cwd()) / project_name.directory

    try:
        project_root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as error:
        raise ProjectExistsError(
            f"Directory '{project_root}' already exists. "
            "Choose a different project name or remove the existing directory."
        ) from error

    try:
        _write_project_files(project_root, project_name)
    except BaseException:
        # Only remove the directory this call created, never pre-existing files.
        shutil.rmtree(project_root, ignore_errors=True)
        raise

    return project_root


def _write_project_files(project_root: Path, project_name: ProjectName) -> None:
    package_dir = project_root / "src" / project_name.package

    files: dict[Path, str] = {
        project_root / "pyproject.toml": templates.pyproject_toml(
            project_name.distribution, project_name.package
        ),
        project_root / ".env": templates.env_file(project_name.distribution),
        project_root / ".gitignore": templates.GITIGNORE,
        project_root / "README.md": templates.readme(
            project_name.directory, project_name.package
        ),
        package_dir / "__init__.py": templates.package_init(project_name.distribution),
        package_dir / "main.py": templates.MAIN_PY,
        package_dir / "config.py": templates.config_py(project_name.distribution),
        package_dir / "database" / "__init__.py": templates.DATABASE_INIT_PY,
        package_dir / "database" / "connection.py": templates.DATABASE_CONNECTION_PY,
    }

    for file_path, content in files.items():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # "x" mode fails instead of overwriting if a file somehow already exists.
        with file_path.open("x", encoding="utf-8") as file:
            file.write(content)
