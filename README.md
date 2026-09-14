# fastapi-foundry

A CLI for scaffolding FastAPI projects.

## Usage

```bash
uv run fastapi-foundry init myproject
cd myproject
uv sync
uv run uvicorn myproject.main:app --reload
```

Hyphenated names are supported: `fastapi-foundry init my-fastapi-app` creates the
`my-fastapi-app/` directory containing the `my_fastapi_app` Python package.

## Development

```bash
uv sync
uv run pytest
```
