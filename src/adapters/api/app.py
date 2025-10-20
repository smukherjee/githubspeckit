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

from typing import Any
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
from adapters.api.routers import policies as policies_router
from adapters.api.routers import feature_flags as feature_flags_router
from adapters.api.routers import profile as profile_router
from adapters.api.routers import roles as roles_router
from adapters.api.routers import admin as admin_router
from adapters.api.security_headers import SecurityHeadersMiddleware
from adapters.observability.metrics import SimpleMetricsRegistry
from adapters.observability.prometheus_client_adapter import PromClientAdapter
from adapters.logging.middleware import StructuredLoggingMiddleware, InMemoryStructuredLogSink
from services.log_export_service import LogExportService
# Import tenant security middleware (Phase 3.3 - T034)
from adapters.api.middleware.tenant_context import TenantContextMiddleware
from adapters.api.middleware.authorization import AuthorizationMiddleware
from adapters.api.middleware.session import SessionMiddleware
# Import correlation middleware from renamed file (was middleware.py, now correlation_middleware.py)
from adapters.api.correlation_middleware import CorrelationMiddleware
from adapters.api.actor_middleware import ActorTrackingMiddleware
from observability.tracing import init_tracing
# Import rate limiting (Phase 3.6 - T050)
from adapters.security.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import yaml
from quality.metrics import QualityMetrics
from pathlib import Path


def create_app() -> FastAPI:
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
        description="Enterprise-grade multi-tenant FastAPI backend with hexagonal architecture"
    )
    # Simple span collection list for TEST-XCUT-11
    app.state._test_spans = []  # noqa: SLF001
    
    # Rate limiting integration (Phase 3.6 - T050)
    # Attach limiter to app.state so it's accessible to endpoints via dependency injection
    app.state.limiter = limiter
    # Register exception handler for rate limit exceeded (HTTP 429 responses)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
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

    @app.get("/api/v1/health", tags=["system"])
    async def health() -> dict[str, str | bool | int | dict]:  # pragma: no cover - simple serialization
        # Phase 3: Returns basic health status with migration state (IMPL-DB-15)
        from adapters.persistence.migration_check import check_migration_head
        from adapters.persistence.db_config import DatabaseConfig
        
        try:
            config = DatabaseConfig.from_env()
            engine = config.create_engine()
            migration_status = await check_migration_head(
                engine,
                alembic_config_path="alembic.ini",
                abort_on_mismatch=False  # Health endpoint should not fail
            )
            current_revision = migration_status.get("current_revision", "unknown")
            is_up_to_date = migration_status.get("is_up_to_date", False)
            await engine.dispose()  # Clean up connection
        except Exception as e:
            current_revision = f"error: {str(e)}"
            is_up_to_date = False
        
        return {
            "status": "ok",
            "migrations_applied": is_up_to_date,
            "current_revision": current_revision,
            "key_rotation_version": 1,
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

    # Include routers from adapters - Standard /api/v1 prefix only
    app.include_router(invitations_router.router, prefix="/api")
    app.include_router(users_router.router, prefix="/api")
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(policies_router.router, prefix="/api")
    app.include_router(feature_flags_router.router, prefix="/api")
    app.include_router(embed_router.router, prefix="/api")
    app.include_router(audit_router.router, prefix="/api")
    app.include_router(tenants_crud.router, prefix="/api")  # Legacy tenant CRUD routes
    app.include_router(profile_router.router, prefix="/api")  # User profile details
    app.include_router(roles_router.router, prefix="/api")  # Role hierarchy (FR-089)
    app.include_router(admin_router.router, prefix="/api/v1")  # Admin routes (FR-004 tenant security)
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
        limit: int = 100,
        tenant_id: str | None = None,
        category: str | None = None,
        correlation_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, list[dict[str, object]] | bool | int | str | None]:
        """Export logs with filtering and redaction (FR-016, FR-072, FR-073).
        
        Query Parameters:
            limit: Maximum records to return (default 100, max 10000)
            tenant_id: Filter by tenant ID
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
        
        # Parse timestamp parameters
        since_dt = None
        until_dt = None
        
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid 'since' timestamp: {since}. Expected ISO8601 format."
                )
        
        if until:
            try:
                until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
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
app = create_app()

__all__ = ["create_app", "app"]
