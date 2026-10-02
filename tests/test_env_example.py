"""Tests for the ``.env.example`` file that ``init`` writes.

``.env`` holds a developer's own credentials and is git-ignored, so
``.env.example`` is the committed copy that tells the next developer which
keys to set.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from fastapi_foundry.generators.project import create_project


def _env_entries(env_file: Path) -> list[tuple[str, str]]:
    """Return the ``KEY=value`` lines of an env file in order."""
    return [
        tuple(line.split("=", 1))
        for line in env_file.read_text().splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    ]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return create_project("my-shop", parent_dir=tmp_path)


def test_env_example_is_generated(project_root: Path) -> None:
    assert (project_root / ".env.example").is_file()


def test_env_example_has_the_same_keys_in_the_same_order_as_env(project_root: Path) -> None:
    example_keys = [key for key, _ in _env_entries(project_root / ".env.example")]
    env_keys = [key for key, _ in _env_entries(project_root / ".env")]

    assert example_keys == env_keys


def test_env_example_lists_each_database_setting(project_root: Path) -> None:
    keys = {key for key, _ in _env_entries(project_root / ".env.example")}

    assert {
        "DB_CONNECTION",
        "DB_HOST",
        "DB_PORT",
        "DB_DATABASE",
        "DB_USERNAME",
        "DB_PASSWORD",
    } <= keys


def test_env_example_holds_the_same_defaults_as_env(project_root: Path) -> None:
    """Copying .env.example to .env gives a project that runs as generated."""
    assert _env_entries(project_root / ".env.example") == _env_entries(project_root / ".env")


def test_env_example_has_no_password(project_root: Path) -> None:
    values = dict(_env_entries(project_root / ".env.example"))

    assert values["DB_PASSWORD"] == ""


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_env_example_is_committed_while_env_is_ignored(project_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=project_root, check=True)

    def is_ignored(name: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "-q", name], cwd=project_root, check=False
        )
        return result.returncode == 0

    assert is_ignored(".env")
    assert not is_ignored(".env.example")


def test_generated_readme_explains_copying_env_example(project_root: Path) -> None:
    assert "cp .env.example .env" in (project_root / "README.md").read_text()
