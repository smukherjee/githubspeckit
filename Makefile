PYTHON := .venv/bin/python
PIP := .venv/bin/pip
UV := uv
APP_MODULE := adapters.api.app:create_app
DEFAULT_PORT ?= 8000
ENV_FILE ?= .env
EXTRA_ENV ?=

.PHONY: venv compile-requirements sync install dev test run api up migrate health env-show clean reset deps-check openapi-bundle openapi-validate openapi-html openapi-serve

venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	@which $(UV) >/dev/null 2>&1 || pip install uv

# Compile a fully hashed requirements lock from pyproject (idempotent)
compile-requirements:
	$(UV) pip compile pyproject.toml -o requirements.txt --generate-hashes

# Sync environment exactly to requirements.txt (removes extraneous pkgs)
sync: venv
	$(UV) pip sync requirements.txt

install: compile-requirements sync

# Add dev/test tooling (keep runtime lock clean)
dev: install
	$(PIP) install --editable . --group dev

test: dev
	$(PYTHON) -m pytest -q

# Show merged environment (base .env + optional env.dev / env.prod)
env-show:
	@echo "--- Base (.env) ---" && grep -v '^#' .env || true
	@if [ -f env.dev ]; then echo "--- env.dev ---"; grep -v '^#' env.dev; fi
	@if [ -f env.prod ]; then echo "--- env.prod ---"; grep -v '^#' env.prod; fi

# Placeholder migration target (extend once Alembic env script present)
migrate: install
	@echo "[migrate] (placeholder) Add Alembic upgrade head here" && true

# Run the API using uvicorn; merges ENV_FILE (default .env) and EXTRA_ENV file if provided
api: dev
	@if [ -f $(ENV_FILE) ]; then set -o allexport; . $(ENV_FILE); set +o allexport; fi; \
	if [ -n "$(EXTRA_ENV)" ] && [ -f "$(EXTRA_ENV)" ]; then set -o allexport; . $(EXTRA_ENV); set +o allexport; fi; \
	$(PYTHON) -c "import uvicorn, importlib; mod,app_fact='$(APP_MODULE)'.split(':'); app_callable=getattr(importlib.import_module(mod), app_fact); uvicorn.run(app_callable(), host='0.0.0.0', port=$(DEFAULT_PORT))"

# Convenience alias
run: api

# End-to-end first boot: deps -> migrate -> run (foreground)
up: install migrate run

health:
	curl -s http://localhost:$(DEFAULT_PORT)/v1/health | jq . || echo "health endpoint not ready"

deps-check: install
	$(UV) pip check

# --- OpenAPI / Swagger Documentation ---
# Combine fragment specs into a single OpenAPI bundle
openapi-bundle: dev
	$(PYTHON) scripts/build_openapi_bundle.py --out specs/001-modern-enterprise-grade/contracts/openapi-combined.yaml

# Validate the combined OpenAPI spec (extend validate script if needed)
openapi-validate: openapi-bundle
	@if [ -f scripts/validate_openapi.py ]; then $(PYTHON) scripts/validate_openapi.py --spec specs/001-modern-enterprise-grade/contracts/openapi-combined.yaml || exit 1; else echo "[warn] validate_openapi.py missing; skipping validation"; fi

# Generate static HTML (ReDoc) into docs/api/index.html
openapi-html: openapi-bundle
	$(PYTHON) scripts/generate_openapi_html.py --spec specs/001-modern-enterprise-grade/contracts/openapi-combined.yaml --out docs/api/index.html

# Serve the generated HTML locally (requires Python http.server)
openapi-serve: openapi-html
	python3 -m http.server 9001 --directory docs/api

# New target: Reset env, install dev, and run tests together without errors
full-setup: reset dev test

reset: clean venv install

clean:
	rm -rf .venv
	find . -name __pycache__ -prune -exec rm -rf {} +
