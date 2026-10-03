"""Tests for ``fastapi-foundry migrate``, ``migrate:rollback`` and ``migrate:status``.

These commands only start the project's own runner through ``uv run``, so
``subprocess.run`` is replaced here; tests/test_migration_runner.py covers
the runner itself.
"""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastapi_foundry import runner
from fastapi_foundry.cli import app
from fastapi_foundry.generators.project import create_project


class FakeRun:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[tuple[list[str], Path]] = []

        self.envs: list[dict[str, str]] = []

    def __call__(
        self, command: list[str], cwd: Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, Path(cwd)))
        self.envs.append(env)
        return subprocess.CompletedProcess(command, self.returncode)


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    fake = FakeRun()
    monkeypatch.setattr(runner.subprocess, "run", fake)
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")
    return fake


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = create_project("myproject", parent_dir=tmp_path)
    monkeypatch.chdir(project_root)
    return project_root


@pytest.mark.parametrize(
    ("command", "action"),
    [("migrate", "migrate"), ("migrate:rollback", "rollback"), ("migrate:status", "status")],
)
def test_command_runs_the_project_runner_with_uv(
    project: Path, fake_run: FakeRun, command: str, action: str
) -> None:
    result = CliRunner().invoke(app, [command])

    assert result.exit_code == 0, result.output
    [(argv, cwd)] = fake_run.calls
    assert argv == ["uv", "run", "--env-file", ".env", "python", "-m", "app.database.migrator", action]
    assert cwd == project


def test_env_file_is_only_passed_when_it_exists(project: Path, fake_run: FakeRun) -> None:
    (project / ".env").unlink()

    CliRunner().invoke(app, ["migrate"])

    [(argv, _)] = fake_run.calls
    assert "--env-file" not in argv


def test_the_callers_virtual_env_is_not_passed_on(
    project: Path, fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Set when fastapi-foundry runs from its own environment; uv would warn
    # that it does not match the project's environment.
    monkeypatch.setenv("VIRTUAL_ENV", "/somewhere/else/.venv")
    monkeypatch.setenv("KEEP_ME", "1")

    CliRunner().invoke(app, ["migrate"])

    [env] = fake_run.envs
    assert "VIRTUAL_ENV" not in env
    assert env["KEEP_ME"] == "1"


def test_runner_exit_code_is_passed_through(project: Path, fake_run: FakeRun) -> None:
    fake_run.returncode = 1

    result = CliRunner().invoke(app, ["migrate"])

    assert result.exit_code == 1


def test_outside_a_project_fails_without_running_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_run: FakeRun
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["migrate"])

    assert result.exit_code == 1
    assert "project's root" in result.output
    assert fake_run.calls == []


def test_project_without_a_runner_explains_how_to_get_one(project: Path, fake_run: FakeRun) -> None:
    (project / "app" / "database" / "migrator.py").unlink()

    result = CliRunner().invoke(app, ["migrate"])

    assert result.exit_code == 1
    assert "app/database/migrator.py" in result.output
    assert fake_run.calls == []


def test_missing_uv_is_reported(
    project: Path, fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)

    result = CliRunner().invoke(app, ["migrate"])

    assert result.exit_code == 1
    assert "uv" in result.output
    assert "python -m app.database.migrator migrate" in result.output
    assert fake_run.calls == []
