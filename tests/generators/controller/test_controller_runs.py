"""Tests that a generated controller serves requests once its route is added.

The route snippet the command prints is appended to the project's
``app/routes.py`` (as a user following the hint would), then a request is
served with ``TestClient`` in a subprocess. This keeps the generically named
``app`` package out of the test session and imports it exactly as uvicorn would.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from fastapi_foundry.generators.controller import create_controller, route_snippet
from fastapi_foundry.generators.project import create_project

REQUEST_SCRIPT = """\
import json
import sys

from fastapi.testclient import TestClient

from app.routes import app

client = TestClient(app)
for path in sys.argv[1:]:
    response = client.get(path)
    print(response.status_code, json.dumps(response.json()))
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return create_project("myproject", parent_dir=tmp_path)


def _add_route(project_root: Path, controller_name: str) -> None:
    routes = project_root / "app" / "routes.py"
    routes.write_text(routes.read_text() + "\n\n" + route_snippet(controller_name))


def _get(project_root: Path, *paths: str) -> list[str]:
    result = subprocess.run(
        [sys.executable, "-c", REQUEST_SCRIPT, *paths],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()


# --- serving requests -----------------------------------------------------


def test_controller_route_serves_its_index(project: Path) -> None:
    create_controller("ProductController", project)
    _add_route(project, "ProductController")

    assert _get(project, "/products") == ['200 {"message": "ProductController index"}']


def test_several_controllers_serve_alongside_the_home_route(project: Path) -> None:
    for name in ("ProductController", "OrderItemController"):
        create_controller(name, project)
        _add_route(project, name)

    assert _get(project, "/", "/products", "/order-items") == [
        '200 {"message": "Hello from fastapi-foundry"}',
        '200 {"message": "ProductController index"}',
        '200 {"message": "OrderItemController index"}',
    ]
