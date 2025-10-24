PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTHON3 := python3.13
UV := uv
APP_MODULE := adapters.api.app:create_app
DEFAULT_PORT ?= 8000
ENV_FILE ?= .env
EXTRA_ENV ?= .env.dev

# Database configuration (override with make DB_URL=... target)
DB_URL ?= postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users
DB_URL_SQLITE ?= sqlite+aiosqlite:///./dev.db

.PHONY: venv compile-requirements sync install dev test run api up migrate health env-show clean reset deps-check openapi-bundle openapi-validate openapi-html openapi-serve
.PHONY: db-create db-drop db-reset db-migrate db-seed db-verify server-start server-stop server-restart bootstrap
.PHONY: security-scan security-baseline security-api security-full security-all
.PHONY: redis-start redis-stop redis-restart redis-cli redis-status redis-flush
.PHONY: docker-up docker-down docker-logs docker-reset docker-build docker-ps docker-shell

venv:
	$(PYTHON3) -m venv .venv
	$(PIP) install --upgrade pip
	@which $(UV) >/dev/null 2>&1 || $(PIP) install uv

# Compile a fully hashed requirements lock from pyproject (idempotent)
compile-requirements:
	$(UV) pip compile pyproject.toml -o requirements.txt --generate-hashes

# Install runtime dependencies from requirements.txt (non-destructive)
sync: venv
	$(PIP) install -r requirements.txt

install: compile-requirements sync

# Add dev/test tooling (keep runtime lock clean)
# Note: Installs dev dependency group which includes pytest-asyncio
# Also ensures Redis is running for rate limiting tests
dev: venv redis-start
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[email]"
	$(PIP) install pytest pytest-asyncio hypothesis coverage ruff mypy types-redis safety radon xenon pyyaml pytest-cov
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "📦 Python packages installed"
	@echo "🔴 Redis running on port 6379"
	@echo ""

test: dev
	@echo "🧪 Running test suite (Redis required for rate limiting tests)..."
	@redis-cli ping >/dev/null 2>&1 || (echo "⚠️  Redis not running. Starting Redis..." && make redis-start)
	$(PYTHON) -m pytest -q

# Show merged environment (base .env + optional env.dev / env.prod)
env-show:
	@echo "--- Base (.env) ---" && grep -v '^#' .env || true
	@if [ -f env.dev ]; then echo "--- env.dev ---"; grep -v '^#' env.dev; fi
	@if [ -f env.prod ]; then echo "--- env.prod ---"; grep -v '^#' env.prod; fi

# --- Database Management ---

# Create PostgreSQL database (idempotent)
db-create:
	@echo "Creating PostgreSQL database..."
	@psql -d postgres -c "SELECT 1 FROM pg_database WHERE datname='infysight_users'" | grep -q 1 || \
		psql -d postgres -c "CREATE DATABASE infysight_users OWNER infysight_dbadmin;"
	@echo "✅ Database infysight_users ready"

# Drop PostgreSQL database (DESTRUCTIVE)
db-drop:
	@echo "⚠️  Dropping PostgreSQL database..."
	@psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'infysight_users' AND pid <> pg_backend_pid();" || true
	@psql -d postgres -c "DROP DATABASE IF EXISTS infysight_users;"
	@echo "✅ Database dropped"

# Reset database: drop, create, migrate, seed
db-reset: db-drop db-create db-migrate db-seed
	@echo "✅ Database reset complete"

# Run Alembic migrations
db-migrate: install
	@echo "Running database migrations..."
	@DATABASE_URL=$(DB_URL) PYTHONPATH=. $(PYTHON) -m alembic upgrade head
	@echo "✅ Migrations complete"

# Seed database with infysight tenant and superadmin user
db-seed: install
	@echo "Seeding database with initial data..."
	@DATABASE_URL=$(DB_URL) $(PYTHON) scripts/seed_infysight.py
	@echo "✅ Database seeded"

# Verify database connection and schema
db-verify: install
	@echo "Verifying database..."
	@PGPASSWORD=infysight_dbadmin123 psql -U infysight_dbadmin -h localhost -d infysight_users -c "\dt" | grep -q tenants && echo "✅ Schema verified" || echo "❌ Schema check failed"
	@PGPASSWORD=infysight_dbadmin123 psql -U infysight_dbadmin -h localhost -d infysight_users -c "SELECT COUNT(*) FROM tenants;" | grep -q 1 && echo "✅ Data verified" || echo "❌ Data check failed"

# --- Server Management ---

# Start API server in background
server-start: dev
	@echo "Starting API server on port $(DEFAULT_PORT)..."
	@export DATABASE_URL=$(DB_URL) && \
		$(PYTHON) -m uvicorn src.$(APP_MODULE) --factory --host 0.0.0.0 --port $(DEFAULT_PORT) --reload > /tmp/githubspeckit-api.log 2>&1 & \
		echo $$! > /tmp/githubspeckit-api.pid
	@sleep 2
	@lsof -ti:$(DEFAULT_PORT) >/dev/null && echo "✅ Server started on http://localhost:$(DEFAULT_PORT)" || echo "❌ Server failed to start (check /tmp/githubspeckit-api.log)"

# Stop API server
server-stop:
	@echo "Stopping API server..."
	@lsof -ti:$(DEFAULT_PORT) | xargs kill -9 2>/dev/null && echo "✅ Server stopped" || echo "ℹ️  No server running on port $(DEFAULT_PORT)"
	@rm -f /tmp/githubspeckit-api.pid

# Restart API server
server-restart: server-stop server-start

# --- Redis Management ---

# Start Redis server in background
redis-start:
	@echo "Starting Redis server..."
	@if lsof -ti:6379 >/dev/null 2>&1; then \
		echo "ℹ️  Redis already running on port 6379"; \
	else \
		redis-server --daemonize yes --port 6379 --dir /tmp --logfile /tmp/redis-server.log && \
		sleep 1 && \
		lsof -ti:6379 >/dev/null && echo "✅ Redis server started on port 6379" || echo "❌ Redis failed to start (check /tmp/redis-server.log)"; \
	fi

# Stop Redis server
redis-stop:
	@echo "Stopping Redis server..."
	@redis-cli shutdown 2>/dev/null && echo "✅ Redis server stopped" || echo "ℹ️  No Redis server running"

# Restart Redis server
redis-restart: redis-stop redis-start

# Open Redis CLI
redis-cli:
	@redis-cli

# Check Redis server status
redis-status:
	@echo "Redis server status:"
	@if redis-cli ping 2>/dev/null | grep -q PONG; then \
		echo "✅ Redis is running"; \
		redis-cli info server | grep -E "redis_version|uptime_in_seconds|tcp_port"; \
	else \
		echo "❌ Redis is not running"; \
	fi

# Flush all Redis data (DESTRUCTIVE - DEV ONLY)
redis-flush:
	@echo "⚠️  Flushing all Redis data..."
	@redis-cli FLUSHALL && echo "✅ All Redis data flushed" || echo "❌ Failed to flush Redis data"

# --- Legacy/Compatibility Targets ---

# Placeholder migration target (use db-migrate instead)
migrate: db-migrate

# Run the API using uvicorn (foreground); merges ENV_FILE (default .env) and EXTRA_ENV file if provided
api: dev
	@if [ -f $(ENV_FILE) ]; then set -o allexport; . $(ENV_FILE); set +o allexport; fi; \
	if [ -n "$(EXTRA_ENV)" ] && [ -f "$(EXTRA_ENV)" ]; then set -o allexport; . $(EXTRA_ENV); set +o allexport; fi; \
	DATABASE_URL=$(DB_URL) $(PYTHON) -c "import uvicorn, importlib; mod,app_fact='$(APP_MODULE)'.split(':'); app_callable=getattr(importlib.import_module(mod), app_fact); uvicorn.run(app_callable(), host='0.0.0.0', port=$(DEFAULT_PORT))"

# Convenience alias
run: api

# End-to-end first boot: deps -> migrate -> run (foreground)
up: install db-migrate run

# --- Bootstrap: Complete Fresh Installation ---

# Complete bootstrap from zero (PostgreSQL)
bootstrap: dev db-reset server-start
	@echo ""
	@echo "=========================================="
	@echo "✅ Bootstrap Complete!"
	@echo "=========================================="
	@echo ""
	@echo "🔑 Login Credentials:"
	@echo "   Email:    infysightsa@infysight.com"
	@echo "   Password: infysightsa123"
	@echo "   Role:     superadmin"
	@echo "   Tenant:   infysight"
	@echo ""
	@echo "🌐 API Server:"
	@echo "   URL:      http://localhost:$(DEFAULT_PORT)"
	@echo "   Health:   http://localhost:$(DEFAULT_PORT)/v1/health"
	@echo "   Docs:     http://localhost:$(DEFAULT_PORT)/docs"
	@echo ""
	@echo "� Redis:"
	@echo "   Port:     6379"
	@echo "   Status:   make redis-status"
	@echo ""
	@echo "�📊 Logs:"
	@echo "   tail -f /tmp/githubspeckit-api.log"
	@echo ""

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
full-dev-setup: reset dev test

reset: clean-cache venv install

clean: clean-cache
	rm -rf .venv

clean-cache:
	find . -name __pycache__ -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f /tmp/githubspeckit-api.pid /tmp/githubspeckit-api.log

# --- OWASP ZAP Security Scanning ---

security-baseline:  ## Run OWASP ZAP baseline (passive) scan - safe for production
	@echo "Running OWASP ZAP baseline scan..."
	@./scripts/security/run-zap-scan.sh baseline

security-api:  ## Run OWASP ZAP API scan with OpenAPI spec
	@echo "Running OWASP ZAP API scan..."
	@./scripts/security/run-zap-scan.sh api

security-full:  ## Run OWASP ZAP full (active) scan - TEST ENVIRONMENT ONLY
	@echo "WARNING: This runs active attacks. Use only in test environments!"
	@./scripts/security/run-zap-scan.sh full --safe

security-authenticated:  ## Run OWASP ZAP authenticated scan (requires AUTH_TOKEN env var)
	@if [ -z "$$AUTH_TOKEN" ]; then \
		echo "ERROR: AUTH_TOKEN environment variable not set"; \
		echo "Usage: AUTH_TOKEN='eyJ...' make security-authenticated"; \
		exit 1; \
	fi
	@echo "Running OWASP ZAP authenticated scan..."
	@./scripts/security/run-zap-scan.sh authenticated --auth-token "$$AUTH_TOKEN"

security-all:  ## Run all OWASP ZAP scans sequentially
	@echo "Running all OWASP ZAP scans..."
	@./scripts/security/run-zap-scan.sh all --verbose

security-scan: security-baseline  ## Alias for security-baseline (default security scan)

# --- Docker Compose Management (V1.0 - Phase 3.9) ---

docker-build:  ## Build Docker images without starting services
	@echo "Building Docker images..."
	@docker-compose build
	@echo "✅ Docker images built"

docker-up:  ## Start all services (PostgreSQL, Redis, pgAdmin, API) in detached mode
	@echo "Starting Docker Compose services..."
	@docker-compose up -d
	@echo ""
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@echo ""
	@echo "=========================================="
	@echo "✅ Docker Compose Services Running"
	@echo "=========================================="
	@echo ""
	@echo "🌐 Services:"
	@echo "   API:      http://localhost:8000"
	@echo "   Health:   http://localhost:8000/v1/health"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   OpenAPI:  http://localhost:8000/openapi.json"
	@echo ""
	@echo "🗄️  Database:"
	@echo "   pgAdmin:  http://localhost:5050"
	@echo "   Login:    admin@example.com / admin"
	@echo "   Host:     postgres (from pgAdmin)"
	@echo "   Port:     5432"
	@echo "   Database: infysight_users"
	@echo "   User:     postgres / postgres"
	@echo ""
	@echo "💾 Cache:"
	@echo "   Redis:    localhost:6379"
	@echo ""
	@echo "📊 View Logs:"
	@echo "   make docker-logs"
	@echo ""
	@echo "🛑 Stop Services:"
	@echo "   make docker-down"
	@echo ""

docker-down:  ## Stop and remove all Docker Compose services
	@echo "Stopping Docker Compose services..."
	@docker-compose down
	@echo "✅ Docker Compose services stopped"

docker-logs:  ## Follow API container logs (Ctrl+C to exit)
	@docker-compose logs -f api

docker-clean:  ## DESTRUCTIVE: Remove githubspeckit containers, images, volumes, and networks only
	@echo "⚠️  DESTRUCTIVE: Removing githubspeckit Docker resources..."
	@echo "Stopping and removing githubspeckit containers..."
	@docker-compose down -v 2>/dev/null || true
	@echo "Removing githubspeckit API image..."
	@docker rmi githubspeckit-api 2>/dev/null || true
	@echo "Removing githubspeckit volumes..."
	@docker volume rm githubspeckit_postgres_data 2>/dev/null || true
	@docker volume rm githubspeckit_redis_data 2>/dev/null || true
	@docker volume rm githubspeckit_pgadmin_data 2>/dev/null || true
	@echo "Removing githubspeckit network..."
	@docker network rm githubspeckit-net 2>/dev/null || true
	@echo ""
	@echo "✅ Githubspeckit Docker resources cleaned"
	@echo "Note: Base images (postgres, redis, pgadmin4) are preserved for reuse"
	@echo ""

docker-reset:  ## Stop, remove volumes (DESTRUCTIVE), rebuild, and start services
	@echo "⚠️  Resetting Docker environment (will delete all data)..."
	@docker-compose down -v
	@docker-compose up --build -d
	@sleep 5
	@echo ""
	@echo "=========================================="
	@echo "✅ Docker Environment Reset Complete"
	@echo "=========================================="
	@echo ""
	@echo "🌐 API:      http://localhost:8000"
	@echo "🗄️  pgAdmin:  http://localhost:5050"
	@echo "📊 Logs:     make docker-logs"
	@echo ""

docker-ps:  ## Show status of all Docker Compose services
	@docker-compose ps

docker-shell:  ## Open shell in running API container
	@docker-compose exec api /bin/sh
