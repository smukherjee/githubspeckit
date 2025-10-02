# githubspeckit-backend

Modern enterprise-grade multi-tenant FastAPI backend (hexagonal, auth core, observability, quality gates).

## Prerequisites

- Python 3.13 or newer (recommended: 3.13)
- pip (comes with Python)
- [uv](https://github.com/astral-sh/uv) (for dependency management)
- GNU Make (for running Makefile targets)

Install `uv` if not present:

```sh
pip install uv
```

## Quickstart for Developers

### 1. Clone the Repository

```sh
git clone <your-repo-url>
cd githubspeckit
```

### 2. Set Up and Install All Dependencies

Use the Makefile to create the virtual environment and install everything needed for development:

```sh
make full-dev-setup
```

This will:

- Remove any old virtual environment and caches
- Create a new `.venv`
- Install all runtime and dev dependencies
- Prepare the project for development and testing

### 3. Set Up Environment Variables

Copy the example env file and adjust as needed:

```sh
cp env.dev .env
```

### 4. Run Database Migrations (if applicable)

```sh
# Placeholder: add migration command if/when implemented
```

### 5. Run the API Server

```sh
make up
```

The server will start on the default port (see `.env` or Makefile).

### 6. Run Tests

```sh
make test
```

### 7. Generate OpenAPI Docs

```sh
make openapi-html
```

## Additional Commands

- `make dev` — Install dev tools (linters, test runners, etc.)
- `make full-dev-setup` — Clean, install, and test in one go
- `make env-show` — Show merged environment variables

## Notes

- All code is under `src/`.
- Tests are under `tests/`.
- Use the provided `.gitignore` to keep your repo clean.
- For more details, see `specs/001-modern-enterprise-grade/quickstart.md`.
