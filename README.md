# githubspeckit-backend

Modern enterprise-grade multi-tenant FastAPI backend (hexagonal, auth core, observability, quality gates).

## Quickstart for Developers

### 1. Clone the Repository
```sh
git clone <your-repo-url>
cd githubspeckit
```

### 2. Create and Activate a Virtual Environment
```sh
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install All Dependencies
```sh
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Copy the example env file and adjust as needed:
```sh
cp env.dev .env
```

### 5. Run Database Migrations (if applicable)
```sh
# Placeholder: add migration command if/when implemented
```

### 6. Run the API Server
```sh
make api
```
The server will start on the default port (see `.env` or Makefile).

### 7. Run Tests
```sh
make test
```

### 8. Generate OpenAPI Docs
```sh
make openapi-html
```

## Additional Commands
- `make dev` — Install dev tools (linters, test runners, etc.)
- `make full-setup` — Clean, install, and test in one go
- `make env-show` — Show merged environment variables

## Notes
- All code is under `src/`.
- Tests are under `tests/`.
- Use the provided `.gitignore` to keep your repo clean.
- For more details, see `specs/001-modern-enterprise-grade/quickstart.md`.
