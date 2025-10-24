# Logging Documentation - V1.0

**Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Log Format**: JSON structured logs  
**Export Endpoint**: `GET /api/v1/logs/export`

---

## Overview

The V1.0 API implements structured JSON logging with tenant isolation, correlation tracking, PII redaction, and security event categorization. Logs are exported via the `/api/v1/logs/export` endpoint with flexible filtering.

### Logging Architecture

```
Application → StructuredLogger → LogBuffer → Export API → ElasticSearch/CloudWatch
                                    ↓
                              PII Redaction Filter
```

- **Format**: JSON lines (one JSON object per line)
- **Storage**: In-memory circular buffer (10,000 entries) + persistent export targets
- **Retention**: 7 days in buffer, 90 days in ElasticSearch/CloudWatch
- **Redaction**: Automatic PII redaction (emails, passwords, tokens)
- **Export**: REST API with time-window filtering + streaming

---

## Log Entry Structure

### Standard Fields

Every log entry contains the following fields:

```json
{
  "timestamp": "2025-10-21T14:23:45.123456Z",
  "level": "INFO",
  "correlation_id": "req-abc123",
  "request_id": "req-abc123",
  "tenant_id": "tenant-456",
  "user_id": "user-789",
  "roles": ["tenant_admin"],
  "method": "GET",
  "path": "/api/v1/admin/users",
  "status": 200,
  "latency_ms": 45.23,
  "category": "api.request",
  "message": "Request completed successfully",
  "context": {
    "query_params": {"limit": 50, "offset": 0},
    "response_size": 2048
  }
}
```

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | ISO8601 | UTC timestamp with microsecond precision | `2025-10-21T14:23:45.123456Z` |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `correlation_id` | string | Request correlation ID for distributed tracing | `req-abc123` |
| `request_id` | string | Unique request identifier (same as correlation_id) | `req-abc123` |
| `tenant_id` | string | Tenant identifier (null for superadmin requests) | `tenant-456` |
| `user_id` | string | User identifier (null for unauthenticated requests) | `user-789` |
| `roles` | array | User roles at request time | `["tenant_admin"]` |
| `method` | string | HTTP method | `GET`, `POST`, `PUT`, `DELETE` |
| `path` | string | Request path (V1.0 admin routes included) | `/api/v1/admin/users` |
| `status` | int | HTTP status code | `200`, `401`, `403`, `500` |
| `latency_ms` | float | Request processing time in milliseconds | `45.23` |
| `category` | string | Log category (dot-notation hierarchy) | `api.request`, `security.auth` |
| `message` | string | Human-readable log message | `Request completed successfully` |
| `context` | object | Additional context (query params, error details, etc.) | `{"query_params": {...}}` |

---

## Log Categories

### API Request Logs (`api.request`)

Standard API request/response logging:

```json
{
  "timestamp": "2025-10-21T14:23:45.123456Z",
  "level": "INFO",
  "correlation_id": "req-abc123",
  "tenant_id": "tenant-456",
  "user_id": "user-789",
  "roles": ["tenant_admin"],
  "method": "GET",
  "path": "/api/v1/admin/users",
  "status": 200,
  "latency_ms": 45.23,
  "category": "api.request",
  "message": "GET /api/v1/admin/users completed in 45ms",
  "context": {
    "query_params": {"limit": 50, "offset": 0},
    "response_size": 2048
  }
}
```

**Query Examples**:
```bash
# All requests for a tenant
GET /api/v1/logs/export?category=api.request&tenant_id=tenant-456

# Slow requests (>500ms)
jq 'select(.category == "api.request" and .latency_ms > 500)' logs.json

# Admin endpoint usage
jq 'select(.path | startswith("/api/v1/admin/"))' logs.json
```

---

### Authentication Logs (`security.auth`)

Login, logout, token refresh, password reset:

```json
{
  "timestamp": "2025-10-21T14:20:00.000Z",
  "level": "INFO",
  "correlation_id": "auth-xyz789",
  "tenant_id": "tenant-456",
  "user_id": null,
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status": 200,
  "category": "security.auth.login",
  "message": "User login successful",
  "context": {
    "email": "[REDACTED]",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

**Subcategories**:
- `security.auth.login` - User login attempts
- `security.auth.logout` - User logout
- `security.auth.token_refresh` - Token refresh
- `security.auth.password_reset` - Password reset requests
- `security.auth.failed_login` - Failed login attempts (CRITICAL for security monitoring)

**Query Examples**:
```bash
# All authentication events
GET /api/v1/logs/export?category=security.auth

# Failed logins (potential brute force)
jq 'select(.category == "security.auth.failed_login")' logs.json

# Failed logins from same IP
jq 'select(.category == "security.auth.failed_login") | .context.ip_address' logs.json | sort | uniq -c | sort -nr
```

---

### Authorization Logs (`security.authz`)

RBAC checks, policy evaluations:

```json
{
  "timestamp": "2025-10-21T14:25:00.000Z",
  "level": "WARNING",
  "correlation_id": "req-def456",
  "tenant_id": "tenant-456",
  "user_id": "user-999",
  "roles": ["user"],
  "category": "security.authz.denied",
  "message": "Access denied: insufficient permissions",
  "context": {
    "required_permission": "users:list",
    "user_roles": ["user"],
    "policy_name": "tenant-isolation-policy"
  }
}
```

**Subcategories**:
- `security.authz.allowed` - Access granted
- `security.authz.denied` - Access denied (403 responses)
- `security.authz.policy_evaluation` - Policy engine evaluations

**Query Examples**:
```bash
# All access denials
GET /api/v1/logs/export?category=security.authz.denied

# Users with most denials (potential privilege escalation attempts)
jq 'select(.category == "security.authz.denied") | .user_id' logs.json | sort | uniq -c | sort -nr | head -10
```

---

### Audit Logs (`audit.*`)

FR-077 audit trail (created/updated metadata):

```json
{
  "timestamp": "2025-10-21T14:30:00.000Z",
  "level": "INFO",
  "correlation_id": "req-ghi789",
  "tenant_id": "tenant-456",
  "user_id": "user-789",
  "category": "audit.user.created",
  "message": "User created",
  "context": {
    "entity_type": "user",
    "entity_id": "user-999",
    "action": "CREATE",
    "changes": {
      "email": "[REDACTED]",
      "roles": ["user"],
      "status": "active"
    }
  }
}
```

**Subcategories**:
- `audit.tenant.*` - Tenant CRUD operations
- `audit.user.*` - User CRUD operations
- `audit.role.*` - Role management
- `audit.policy.*` - Policy CRUD operations

**Query Examples**:
```bash
# All audit events for a tenant
GET /api/v1/logs/export?category=audit&tenant_id=tenant-456

# User creation events
jq 'select(.category == "audit.user.created")' logs.json

# Changes by specific admin
jq 'select(.category | startswith("audit.")) | select(.user_id == "user-789")' logs.json
```

---

### Database Logs (`db.*`)

Query execution, connection pool, migrations:

```json
{
  "timestamp": "2025-10-21T14:35:00.000Z",
  "level": "DEBUG",
  "correlation_id": "req-jkl012",
  "category": "db.query",
  "message": "Query executed",
  "context": {
    "table": "users",
    "operation": "SELECT",
    "duration_ms": 12.5,
    "rows_affected": 50
  }
}
```

**Subcategories**:
- `db.query` - SQL query execution
- `db.migration` - Alembic migrations
- `db.connection_pool` - Connection pool events

**Query Examples**:
```bash
# Slow queries (>100ms)
jq 'select(.category == "db.query" and .context.duration_ms > 100)' logs.json

# Most queried tables
jq 'select(.category == "db.query") | .context.table' logs.json | sort | uniq -c | sort -nr
```

---

### Error Logs (`error.*`)

Application errors, exceptions, stack traces:

```json
{
  "timestamp": "2025-10-21T14:40:00.000Z",
  "level": "ERROR",
  "correlation_id": "req-mno345",
  "tenant_id": "tenant-456",
  "user_id": "user-789",
  "method": "POST",
  "path": "/api/v1/admin/users",
  "status": 500,
  "category": "error.internal",
  "message": "Internal server error",
  "context": {
    "exception_type": "DatabaseError",
    "exception_message": "Connection timeout",
    "stack_trace": "Traceback (most recent call last):\n  File..."
  }
}
```

**Subcategories**:
- `error.internal` - 500 errors
- `error.client` - 4xx errors (400, 404, 422)
- `error.timeout` - Request timeouts
- `error.validation` - Input validation errors

---

## V1.0 Admin Routes Logging

### New Admin Endpoints

All V1.0 admin routes are logged with `api.request` category and admin-specific context:

| Endpoint | Log Example |
|----------|-------------|
| `GET /api/v1/admin/tenants` | `{"path": "/api/v1/admin/tenants", "method": "GET", "roles": ["superadmin"]}` |
| `POST /api/v1/admin/tenants` | `{"path": "/api/v1/admin/tenants", "method": "POST", "context": {"tenant_name": "..."}}}` |
| `GET /api/v1/admin/users` | `{"path": "/api/v1/admin/users", "query_params": {"tenant_id": "tenant-456"}}` |
| `POST /api/v1/admin/users` | `{"path": "/api/v1/admin/users", "context": {"email": "[REDACTED]"}}` |
| `GET /api/v1/admin/policies` | `{"path": "/api/v1/admin/policies", "tenant_id": "tenant-456"}` |
| `GET /api/v1/admin/roles` | `{"path": "/api/v1/admin/roles", "tenant_id": "tenant-456"}` |
| `POST /api/v1/admin/roles` | `{"path": "/api/v1/admin/roles", "context": {"role_name": "..."}}` |
| `POST /api/v1/admin/users/{id}/roles/{role_id}` | `{"path": "/api/v1/admin/users/{id}/roles/{role_id}", "context": {"user_id": "...", "role_id": "..."}}` |

**Admin Route Query Examples**:
```bash
# All admin endpoint usage
GET /api/v1/logs/export?path_prefix=/api/v1/admin/

# Superadmin actions only
jq 'select(.path | startswith("/api/v1/admin/")) | select(.roles | contains(["superadmin"]))' logs.json

# Admin 403 errors (unauthorized admin access)
jq 'select(.path | startswith("/api/v1/admin/")) | select(.status == 403)' logs.json

# Tenant admin actions per tenant
jq 'select(.path | startswith("/api/v1/admin/")) | select(.roles | contains(["tenant_admin"])) | {tenant_id, path, method}' logs.json
```

---

## Log Export API

### Endpoint: `GET /api/v1/logs/export`

**Authentication**: Requires `admin` role (tenant_admin or superadmin)

**Query Parameters**:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `start_time` | ISO8601 | Start of time window (inclusive) | `2025-10-21T00:00:00Z` |
| `end_time` | ISO8601 | End of time window (exclusive) | `2025-10-21T23:59:59Z` |
| `category` | string | Filter by log category (prefix match) | `security.auth`, `audit` |
| `tenant_id` | string | Filter by tenant (superadmin: any, tenant_admin: own only) | `tenant-456` |
| `user_id` | string | Filter by user | `user-789` |
| `level` | string | Filter by log level | `ERROR`, `WARNING` |
| `correlation_id` | string | Filter by correlation ID (for request tracing) | `req-abc123` |
| `path_prefix` | string | Filter by path prefix | `/api/v1/admin/` |
| `limit` | int | Max number of entries (default 1000, max 10000) | `5000` |

**Response Format**:
```
Content-Type: application/x-ndjson

{"timestamp": "...", "level": "INFO", ...}
{"timestamp": "...", "level": "ERROR", ...}
...
```

**Example Requests**:
```bash
# Export all logs for last 24 hours
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/logs/export?start_time=2025-10-20T00:00:00Z&end_time=2025-10-21T00:00:00Z"

# Export failed logins for a tenant
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/logs/export?category=security.auth.failed_login&tenant_id=tenant-456"

# Export all errors with correlation ID
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/logs/export?level=ERROR&correlation_id=req-abc123"

# Export admin endpoint usage
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/logs/export?path_prefix=/api/v1/admin/"
```

---

## PII Redaction

### Automatic Redaction

The following fields are automatically redacted in logs:

| Field Pattern | Redacted Value | Example |
|---------------|----------------|---------|
| `email` | `[REDACTED]` | `user@example.com` → `[REDACTED]` |
| `password` | `[REDACTED]` | `Pa$$w0rd` → `[REDACTED]` |
| `token` | `[REDACTED_TOKEN]` | `eyJhbGc...` → `[REDACTED_TOKEN]` |
| `refresh_token` | `[REDACTED_TOKEN]` | `eyJhbGc...` → `[REDACTED_TOKEN]` |
| `api_key` | `[REDACTED_KEY]` | `sk_live_abc123` → `[REDACTED_KEY]` |
| `ssn` | `[REDACTED_SSN]` | `123-45-6789` → `[REDACTED_SSN]` |
| `credit_card` | `[REDACTED_CC]` | `4111-1111-1111-1111` → `[REDACTED_CC]` |

### Redaction Rules

Redaction rules are configurable via the configuration descriptor:

```toml
[logging.redaction]
enabled = true
fields = ["email", "password", "token", "refresh_token"]
patterns = [
  { regex = "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", replacement = "[REDACTED_EMAIL]" },
  { regex = "\bsk_live_[A-Za-z0-9]{32}\b", replacement = "[REDACTED_KEY]" }
]
```

**Example Redacted Log**:
```json
{
  "timestamp": "2025-10-21T14:45:00.000Z",
  "level": "INFO",
  "category": "security.auth.login",
  "message": "User login successful",
  "context": {
    "email": "[REDACTED]",
    "password": "[REDACTED]",
    "ip_address": "192.168.1.100"
  }
}
```

---

## Log Analysis Examples

### Security Analytics

#### Identify Brute Force Attacks
```bash
# Failed logins grouped by IP
jq -r 'select(.category == "security.auth.failed_login") | .context.ip_address' logs.json | sort | uniq -c | sort -nr

# Example output:
# 45 192.168.1.100
# 12 192.168.1.101
#  3 192.168.1.102
```

#### Track Privilege Escalation Attempts
```bash
# Users with most 403 errors
jq -r 'select(.status == 403) | .user_id' logs.json | sort | uniq -c | sort -nr | head -10
```

#### Monitor Suspicious API Access
```bash
# Admin endpoint access by non-admin roles
jq 'select(.path | startswith("/api/v1/admin/")) | select(.roles | contains(["user"]))' logs.json
```

---

### Performance Analytics

#### Identify Slow Endpoints
```bash
# p95 latency by endpoint
jq -r 'select(.category == "api.request") | "\(.path) \(.latency_ms)"' logs.json | \
  awk '{sum[$1]+=$2; count[$1]++} END {for (path in sum) print path, sum[path]/count[path]}' | \
  sort -k2 -nr | head -10
```

#### Database Query Performance
```bash
# Slow queries (>100ms)
jq 'select(.category == "db.query" and .context.duration_ms > 100) | {table: .context.table, duration_ms: .context.duration_ms}' logs.json
```

---

### Tenant Analytics

#### Tenant Activity
```bash
# Request count per tenant
jq -r 'select(.category == "api.request") | .tenant_id' logs.json | sort | uniq -c | sort -nr

# Example output:
# 1543 tenant-456
#  892 tenant-789
#  234 tenant-abc
```

#### Tenant Error Rates
```bash
# Error rate by tenant
jq -r 'select(.status >= 500) | .tenant_id' logs.json | sort | uniq -c | sort -nr
```

---

## Structured Logging Best Practices

### DO:
- ✅ Use JSON structured logs for machine parsing
- ✅ Include correlation IDs for distributed tracing
- ✅ Log all authentication/authorization events
- ✅ Redact PII (emails, passwords, tokens)
- ✅ Include latency_ms for performance monitoring
- ✅ Use hierarchical categories (`security.auth.login`, not `login`)
- ✅ Log context (query params, error details) in `context` field

### DON'T:
- ❌ Log sensitive data (passwords, tokens, credit cards) without redaction
- ❌ Use unstructured log messages (`"User logged in"` → `{"category": "security.auth.login", "user_id": "..."}`)
- ❌ Log excessive DEBUG entries in production (use INFO+)
- ❌ Log PII in message field (use redacted context)
- ❌ Use vague categories (`misc`, `other`)

---

## Integration Examples

### ElasticSearch

```bash
# Stream logs to ElasticSearch
curl -X GET "http://localhost:8000/api/v1/logs/export?start_time=2025-10-21T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN" | \
while read line; do
  curl -X POST "http://localhost:9200/logs/_doc" \
    -H "Content-Type: application/json" \
    -d "$line"
done
```

### CloudWatch Logs

```bash
# Export logs to CloudWatch
aws logs put-log-events \
  --log-group-name "/aws/ecs/githubspeckit" \
  --log-stream-name "api-$(date +%Y-%m-%d)" \
  --log-events "$(curl -s "http://localhost:8000/api/v1/logs/export" -H "Authorization: Bearer $TOKEN" | jq -s '[.[] | {timestamp: (.timestamp | fromdate * 1000), message: tojson}]')"
```

### Splunk

```bash
# Forward logs to Splunk HEC
curl -X GET "http://localhost:8000/api/v1/logs/export" \
  -H "Authorization: Bearer $TOKEN" | \
while read line; do
  curl -X POST "https://splunk.example.com:8088/services/collector/event" \
    -H "Authorization: Splunk $SPLUNK_TOKEN" \
    -d "{\"event\": $line}"
done
```

---

## Troubleshooting

### Common Issues

#### Issue 1: No Logs Returned
**Symptom**: `GET /api/v1/logs/export` returns empty array  
**Cause**: Time window outside log retention (7 days)  
**Solution**: Check `start_time`/`end_time` parameters

#### Issue 2: Missing Correlation IDs
**Symptom**: `correlation_id` field is `null`  
**Cause**: Request missing `X-Correlation-ID` header  
**Solution**: Add header to client requests

#### Issue 3: PII Leakage
**Symptom**: Emails/passwords appear in logs  
**Cause**: Redaction disabled or misconfigured  
**Solution**: Check `logging.redaction.enabled` in descriptor.toml

---

## References

- [Structured Logging Best Practices](https://www.structlog.org/)
- [JSON Lines Format](https://jsonlines.org/)
- [OpenTelemetry Logging](https://opentelemetry.io/docs/concepts/signals/logs/)
- [V1.0 Metrics Documentation](./METRICS.md)
- [V1.0 API Routes](../README.md#api-endpoints)

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Maintainer**: Platform Team
