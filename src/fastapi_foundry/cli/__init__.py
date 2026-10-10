"""Command-line interface for fastapi-foundry.

This package only handles CLI concerns: argument parsing, user-facing output
and exit codes. All project-generation logic lives in ``fastapi_foundry.generators``.
"""

from fastapi_foundry.cli.main import app

__all__ = ["app"]
