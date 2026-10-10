"""Tests that a generated model works against the table its migration creates.

The project's migrations are applied, then the model is used through the
project's own ``SessionLocal``, all in a subprocess against a SQLite file. This
keeps the generically named ``app`` package out of the test session and needs
no database server.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from fastapi_foundry.generators.model import create_model
from fastapi_foundry.generators.project import create_project

USE_USER_MODEL = """\
from sqlalchemy import select

from app.config.sqlalchemy_connection import SessionLocal
from app.model.user_model import UserModel

with SessionLocal() as session:
    session.add(UserModel())
    session.commit()
    user = session.scalars(select(UserModel)).one()
    assert user.id == 1, user.id
    assert user.created_at is not None
    assert user.updated_at is not None
print("ok")
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return create_project("myproject", parent_dir=tmp_path)


def _run(project_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{project_root / 'test.sqlite'}"}
    return subprocess.run(
        [sys.executable, *args], cwd=project_root, env=env, capture_output=True, text=True
    )


# --- running the model ----------------------------------------------------


def test_model_reads_and_writes_the_migrated_table(project: Path) -> None:
    create_model("UserModel", "users", project)

    migrated = _run(project, ["-m", "app.database.migrator", "migrate"])
    assert migrated.returncode == 0, migrated.stderr

    used = _run(project, ["-c", USE_USER_MODEL])
    assert used.returncode == 0, used.stderr
    assert used.stdout.strip() == "ok"


def test_models_import_alongside_the_app(project: Path) -> None:
    create_model("UserModel", "users", project)
    create_model("ProductModel", "products", project)

    script = (
        "from app.routes import app\n"
        "from app.model.base import Base\n"
        "from app.model.user_model import UserModel\n"
        "from app.model.product_model import ProductModel\n"
        "print(sorted(Base.metadata.tables))\n"
    )
    result = _run(project, ["-c", script])

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['products', 'users']"
