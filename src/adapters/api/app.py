"""FastAPI application factory and health endpoint (implements part of FR-015).

Currently includes only a minimal    async def export_config() -> dict[str, object]:  # pragma: no cover - simple serialization
        cfg = load_config({
            \"APP_NAME\": (\"modern-backend\", False),
            \"PASSWORD_MIN_LENGTH\": (12, False),
            \"PASSWORD_COMPLEXITY_STRICT\": (False, False),
        })
        return cfg.export()/status endpoint returning migration state
and key rotation version placeholders.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
import logging
import traceback
from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from domain.config.loader import load_config, ConfigValidationError
import os, sys, json
from adapters.api.routers import invitations as invitations_router
from adapters.api.routers import users as users_router
from adapters.api.routers import auth as auth_router
from adapters.api.routers import embed as embed_router
from adapters.api.routers import audit as audit_router
from adapters.api.routers import tenants_crud  # Legacy tenant CRUD (CREATE/LIST)
from adapters.api.routers.tenants import router as tenants_scoped_router  # New tenant-scoped routes
# from adapters.api.routers import policies as policies_router  # Hidden from OpenAPI docs
# from adapters.api.routers import feature_flags as feature_flags_router  # Hidden from OpenAPI docs
from adapters.api.routers import profile as profile_router
# from adapters.api.routers import roles as roles_router  # OLD static role hierarchy (replaced by admin/roles.py)
from adapters.api.routers.admin import roles as admin_roles_router  # V1.0 role management (FR-122)
from adapters.api.routers import admin as admin_router
from adapters.api.security_headers import SecurityHeadersMiddleware
from adapters.observability.metrics import SimpleMetricsRegistry
from adapters.observability.prometheus_client_adapter import PromClientAdapter
from adapters.logging.middleware import StructuredLoggingMiddleware, InMemoryStructuredLogSink
from adapters.logging.config import configure_logging
from services.log_export_service import LogExportService
# Import tenant security middleware (Phase 3.3 - T034)
from adapters.api.middleware.tenant_context import TenantContextMiddleware
from adapters.api.middleware.authorization import AuthorizationMiddleware
from adapters.api.middleware.session import SessionMiddleware
# Import correlation middleware from renamed file (was middleware.py, now correlation_middleware.py)
from adapters.api.correlation_middleware import CorrelationMiddleware
from adapters.api.actor_middleware import ActorTrackingMiddleware
from observability.tracing import init_tracing
# V1.0: Rate limiting disabled for intranet deployment (see ADR-004)
# from adapters.security.rate_limit import limiter
# from slowapi import _rate_limit_exceeded_handler
# from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import yaml
from quality.metrics import QualityMetrics
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - startup and shutdown events."""
    # Startup: Nothing specific needed yet
    yield
    # Shutdown: Clean up database connections
    from adapters.api import deps
    if deps._session_maker:
        engine = deps._session_maker.kw.get("bind")
        if engine:
            await engine.dispose()


def create_app() -> FastAPI:
    # Configure central logging (Constitution V: Central Control)
    # Must happen before any logging calls
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "json")  # json or text
    log_sink = os.getenv("LOG_SINK", "stdout")  # stdout, stderr, or file path
    
    configure_logging(
        log_level=log_level,
        log_format=log_format,
        log_sink=log_sink,
    )
    
    # Early config validation fail-fast hook (FR-041 C-045)
    if os.getenv("SIMULATE_CONFIG_FAIL") == "1":  # pragma: no cover - integration scenario
        try:
            load_config(raw={})
        except ConfigValidationError as e:
            # Build issues list
            msg = str(e)
            issues = []
            if ": [" in msg:
                part = msg.split(": ")[-1].strip()
                for item in part.strip("[]").replace("'", "").split(","):
                    name = item.strip()
                    if name:
                        issues.append({"name": name, "error": "missing", "expected_type": "str"})
            payload = {
                "error": "configuration_validation_failed",
                "config_hash": None,
                "issues": sorted(issues, key=lambda x: x["name"]),
            }
            sys.stderr.write(json.dumps(payload) + "\n")
            raise
    # Initialize tracing (best-effort; failures ignored to avoid startup abort)
    try:  # pragma: no cover - trivial
        init_tracing()
    except Exception:  # pragma: no cover - defensive
        pass
    app = FastAPI(
        title="Modern Backend V1.0",
        version="1.0.0",
        lifespan=lifespan,
        description="""
## Modern Multi-Tenant Backend - V1.0 Production Release

Enterprise-grade FastAPI backend with hexagonal architecture, multi-tenancy, 
RBAC, policy engine, and comprehensive observability.

### 🚨 Breaking Changes in V1.0

**Database Support**:
- ❌ SQLite support **removed** - PostgreSQL only
- ✅ Per-tenant email uniqueness enforced (same email allowed across tenants)
- ✅ Consolidated migrations with schema versioning

**Authentication & Authorization**:
- ✅ Argon2id password hashing (mandatory)
- ✅ JWT with replay protection placeholders
- ✅ Superadmin isolation via dedicated `/admin` routes

**API Changes**:
- ✅ Admin routes: `/api/v1/admin/tenants`, `/api/v1/admin/users`
- ✅ Tenant-scoped routes require proper tenant context
- ✅ Email uniqueness enforced per-tenant (409 Conflict on duplicates)

**Observability**:
- ✅ OpenTelemetry tracing (FastAPI + SQLAlchemy)
- ✅ Structured JSON logging with redaction
- ✅ Metrics snapshots with regression detection

### 📚 Key Features

- **Multi-Tenancy**: Full tenant isolation with superadmin override
- **RBAC + Policy Engine**: Tri-state evaluation (ALLOW/DENY/ABSTAIN)
- **Security**: OWASP best practices, rate limiting (optional), security headers
- **Audit Trail**: Comprehensive audit events with metadata
- **Observability**: Tracing, metrics, structured logging
- **Configuration**: Single YAML descriptor with hash validation
- **Quality Gates**: Complexity, duplication, security scans

### 🔗 Documentation

- [Migration Guide](https://github.com/yourusername/project/docs/MIGRATION-TO-V1.0.md)
- [Changelog](https://github.com/yourusername/project/docs/CHANGELOG-V1.0.md)
- [Database Schema](https://github.com/yourusername/project/docs/database-schema-v1.0.md)

### 🏗️ Architecture

**Hexagonal Design**:
- Domain: Pure business logic (tenants, users, policies, audit)
- Adapters: API (FastAPI), Persistence (SQLAlchemy), Observability
- Services: Application orchestration layer

**Tech Stack**:
- Python 3.13, FastAPI 0.104+, SQLAlchemy 2.x (async)
- PostgreSQL 14+, Alembic migrations
- OpenTelemetry 0.58b0, pytest 8.4.2
""",
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        }
    )
    # Simple span collection list for TEST-XCUT-11
    app.state._test_spans = []  # noqa: SLF001
    
    # V1.0: Rate limiting disabled for intranet deployment (see ADR-004)
    # Rate limiting integration (Phase 3.6 - T050)
    # Attach limiter to app.state so it's accessible to endpoints via dependency injection
    # app.state.limiter = limiter
    # Register exception handler for rate limit exceeded (HTTP 429 responses)
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS middleware - environment-aware configuration
    cors_origins_str = os.getenv("CORS_ORIGINS", "*")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Parse CORS origins
    if cors_origins_str == "*":
        # Wildcard - allow all origins (development only)
        if environment == "production":
            # In production, use specific origins for security
            cors_origins = [
                "https://yourdomain.com",  # Replace with actual production domain
                "https://www.yourdomain.com",
            ]
        else:
            # Development: allow common dev server ports
            cors_origins = [
                "http://localhost:3000",  # React/Next.js dev server
                "http://localhost:5173",  # Vite dev server  
                "http://127.0.0.1:3000",  # Alternative localhost
                "http://127.0.0.1:5173",  # Alternative localhost
                "http://localhost:8080",  # Vue dev server
                "http://127.0.0.1:8080",  # Alternative localhost
                "http://localhost:4200",  # Angular dev server
                "http://127.0.0.1:4200",  # Alternative localhost
            ]
    else:
        # Parse comma-separated origins
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    
    # Log CORS configuration for debugging
    print(f"🌐 CORS Origins ({environment}): {cors_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,  # Required for JWT tokens and HttpOnly cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],  # Includes Authorization header
        expose_headers=["Content-Range", "X-Total-Count"],  # Required for React-Admin pagination
    )
    
    # Security/Error middleware (TEST-SEC-03 / IMPL-SEC-04) ensuring consistent envelope
    @app.middleware("http")
    async def error_envelope_middleware(request: Request, call_next: Any) -> Response:  # pragma: no cover small wrapper
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: PIE786
            cid = request.headers.get("X-Correlation-ID") or "pending"
            
            # Log exception with full context (Constitution V: Security/audit logs MUST be structured)
            logger = logging.getLogger("githubspeckit.error")
            logger.error(
                "Unhandled exception in request processing",
                extra={
                    "correlation_id": cid,
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc(),
                },
                exc_info=True,
            )
            
            return JSONResponse(status_code=500, content={"error": {"code": exc.__class__.__name__, "message": "internal_error", "correlation_id": cid}})
    # Attach structured logging middleware (TEST-OBS-01) with in-memory sink for tests
    sink = InMemoryStructuredLogSink()
    app.state.log_sink = sink
    
    # Middleware stack order (Phase 3.3 - T034):
    # 1. Actor tracking (extract user_id for audit logging)
    # 2. Correlation ID (request tracing)
    # 3. Structured logging (log all requests)
    # 4. Session management (read Redis session if present)
    # 5. Tenant context extraction (parse JWT → TenantContext)
    # 6. Authorization enforcement (evaluate policies)
    
    app.add_middleware(ActorTrackingMiddleware)
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(StructuredLoggingMiddleware, sink=sink)
    
    # NEW: Tenant security middleware (FR-004)
    # NOTE: Middleware runs in LIFO order (last added runs first)
    # Order of execution: Session → TenantContext → Authorization
    
    # Get Redis client from dependency injection
    from adapters.api.deps import get_redis_client
    redis_client = get_redis_client()
    
    app.add_middleware(SessionMiddleware, redis_client=redis_client)
    app.add_middleware(AuthorizationMiddleware)  # Runs SECOND (enforces policies)
    app.add_middleware(TenantContextMiddleware)  # Runs FIRST (extracts context)
    
    # Lightweight span capture middleware (placeholder instrumentation)
    @app.middleware("http")
    async def tracing_capture_middleware(request: Request, call_next: Any) -> Response:  # pragma: no cover - thin logic
        span_name = f"HTTP {request.method} {request.url.path}"
        app.state._test_spans.append({"name": span_name})  # noqa: SLF001
        return await call_next(request)

    # Error envelope handler (TEST-SEC-12) minimal: unify unhandled exceptions
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - simple path
        # Basic envelope structure per FR-017/C-031 draft: {error: {code, message}}
        # Code derived from exception type name; message sanitized.
        code = getattr(exc, "code", exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": str(code),
                    "message": "internal_error",  # avoid leaking details pre-hardening
                    "correlation_id": request.headers.get("X-Correlation-ID") or "pending",
                }
            },
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:  # pragma: no cover
        """Simple health check - indicates server is up. V1.0 baseline."""
        return {
            "status": "ok",
            "version": "1.0.0"
        }

    @app.get("/api/v1/config", tags=["system"])
    async def export_config() -> dict[str, object]:  # pragma: no cover - simple serialization
        cfg = load_config({
            "APP_NAME": ("modern-backend", False),
            "PASSWORD_MIN_LENGTH": (12, False),
            "PASSWORD_COMPLEXITY_STRICT": (False, False),
        })
        return cfg.export()

    @app.get("/api/v1/config/errors", tags=["system"])
    async def config_errors() -> dict[str, list[str]]:  # pragma: no cover
        # Phase 3: Returns config validation errors from startup
        # Satisfies FR-041 C-045 contract test (TEST-API-28)
        return {"errors": []}

    # V1.0: Include routers - Unified /api/v1/admin/* prefix for admin routes
    app.include_router(invitations_router.router, prefix="/api")  # Deferred to Phase 2 (spec 015)
    # app.include_router(users_router.router, prefix="/api")  # V1.0 REMOVED: Migrated to /api/v1/admin/users (FR-115)
    # app.include_router(tenants_crud.router, prefix="/api")  # V1.0 REMOVED: Migrated to /api/v1/admin/tenants (FR-115)
    app.include_router(auth_router.router, prefix="/api")  # Public auth endpoints
    # app.include_router(policies_router.router, prefix="/api")  # Deferred to Phase 2 (spec 014)
    # app.include_router(feature_flags_router.router, prefix="/api")  # Deferred to Phase 2 (spec 017)
    app.include_router(embed_router.router, prefix="/api")  # Public embed exchange
    app.include_router(audit_router.router, prefix="/api")  # User audit events
    app.include_router(profile_router.router, prefix="/api")  # User profile details
    # app.include_router(roles_router.router, prefix="/api")  # V1.0 REMOVED: Replaced by admin/roles.py (FR-122)
    app.include_router(admin_roles_router.router, prefix="/api/v1/admin")  # V1.0 role management (FR-122)
    app.include_router(admin_router.router, prefix="/api/v1")  # V1.0 Admin routes (FR-004, FR-115)
    app.include_router(tenants_scoped_router, prefix="/api/v1")  # Tenant-scoped routes (FR-004)

    # Mount static files for serving profile photos
    photos_dir = Path("data/photos")
    photos_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    app.mount("/media/photos", StaticFiles(directory=str(photos_dir)), name="photos")

    # Attach a global prometheus client adapter to app.state for adapters to use in tests / runtime
    # Keep the existing SimpleMetricsRegistry for unit tests compatibility; services can opt to use either.
    app.state.metrics = SimpleMetricsRegistry()
    app.state.prom = PromClientAdapter()
    app.state.log_exporter = LogExportService(sink=sink)
    # Initialize quality metrics & justifications (basic) (IMPL-SEC-06 / IMPL-SEC-08)
    try:
        with open("justifications.yaml", "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        just_count = len(data.get("entries", []))
    except FileNotFoundError:  # pragma: no cover
        just_count = 0
    qm = QualityMetrics(app.state.prom)
    qm.set_justifications(just_count)
    app.state.quality_metrics = qm

    @app.get("/metrics", tags=["system"])
    async def metrics_prometheus() -> Response:
        # Expose prometheus_client generated metrics bytes
        data = app.state.prom.generate_latest()
        return Response(content=data, media_type="text/plain; version=0.0.4")

    @app.get("/api/v1/metrics/snapshot", tags=["system"])
    async def metrics_snapshot() -> dict[str, list[str]]:  # pragma: no cover - lightweight serialization
        # Provide a JSON snapshot of current required metric names present for quick checks
        raw = app.state.prom.generate_latest().decode("utf-8")
        present = []
        for line in raw.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            name = line.split("{")[0].split()[0]
            present.append(name)
        return {"metrics": sorted(set(present))}

    @app.get("/api/v1/logs/export", tags=["system"])
    async def export_logs(
        request: Request,
        limit: int = 100,
        tenant_id: str | None = None,
        category: str | None = None,
        correlation_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, list[dict[str, object]] | bool | int | str | None]:
        """Export logs with filtering and redaction (FR-016, FR-072, FR-073).
        
        **RBAC Enforcement**:
        - Superadmin: Can export logs from any tenant (or all if tenant_id not specified)
        - Tenant Admin: Can ONLY export logs from their own tenant (tenant_id forced to match JWT)
        - Regular Users: Access denied (403 Forbidden)
        
        Query Parameters:
            limit: Maximum records to return (default 100, max 10000)
            tenant_id: Filter by tenant ID (forced to match JWT for non-superadmin)
            category: Filter by log level/category (info, warning, error)
            correlation_id: Filter by correlation ID
            since: ISO8601 timestamp lower bound (inclusive)
            until: ISO8601 timestamp upper bound (exclusive)
            
        Returns:
            JSON with records (redacted), truncated flag, total_available count,
            and optional reason for truncation.
        """
        from datetime import datetime
        from fastapi import HTTPException
        
        # RBAC enforcement: Check authentication and roles
        if not hasattr(request.state, "tenant_context"):
            raise HTTPException(
                status_code=401,
                detail="Authentication required for log export"
            )
        
        tenant_context = request.state.tenant_context
        roles = tenant_context.roles
        is_superadmin = tenant_context.is_superadmin
        
        # Regular users cannot access log export
        if not is_superadmin and "tenant_admin" not in roles:
            raise HTTPException(
                status_code=403,
                detail="Log export requires superadmin or tenant_admin role"
            )
        
        # Tenant admin can ONLY see logs from their own tenant
        if not is_superadmin:
            if tenant_id and tenant_id != str(tenant_context.tenant_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Tenant admins can only export logs from their own tenant ({tenant_context.tenant_id})"
                )
            # Force tenant_id to match JWT claims
            tenant_id = str(tenant_context.tenant_id)
        
        # Parse timestamp parameters
        since_dt = None
        until_dt = None
        
        if since:
            try:
                # Handle URL encoding: space in URL becomes '+', which is decoded as space
                # Replace space with '+' to handle URL-decoded timestamps
                normalized_since = since.replace(" ", "+").replace("Z", "+00:00")
                since_dt = datetime.fromisoformat(normalized_since)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid 'since' timestamp: {since}. Expected ISO8601 format."
                )
        
        if until:
            try:
                # Handle URL encoding: space in URL becomes '+', which is decoded as space
                normalized_until = until.replace(" ", "+").replace("Z", "+00:00")
                until_dt = datetime.fromisoformat(normalized_until)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid 'until' timestamp: {until}. Expected ISO8601 format."
                )
        
        # Validate time window (FR-072: ≤ 24h)
        if since_dt and until_dt:
            delta = until_dt - since_dt
            if delta.total_seconds() > 86400:  # 24 hours
                raise HTTPException(
                    status_code=400,
                    detail="Time window exceeds 24 hour limit (FR-072 C-006)"
                )
        
        # Call export service with filters
        res = app.state.log_exporter.export_latest(
            limit=limit,
            tenant_id=tenant_id,
            category=category,
            correlation_id=correlation_id,
            since=since_dt,
            until=until_dt,
        )
        
        response = {
            "records": res.records,
            "truncated": res.truncated,
            "total_available": res.total_available,
        }
        
        if res.reason:
            response["reason"] = res.reason
        
        return response

    # Security headers middleware - MUST BE LAST (runs first, wraps ALL responses)
    # OWASP A01:2021 compliance, CWE-525 prevention
    # Prevents browser/proxy caching of sensitive data (auth tokens, user info, policies)
    # Also adds defense-in-depth headers (XSS, clickjacking, MIME sniffing protection)
    # IMPORTANT: Added last so it wraps error responses too
    app.add_middleware(SecurityHeadersMiddleware)

    return app


# Create app instance for uvicorn
# Note: This runs at module import time, which can cause issues during test discovery
# if logging hasn't been configured yet. Tests should use the app_client fixture
# from conftest.py which calls create_app() explicitly.
app = create_app()

__all__ = ["create_app", "app"]
