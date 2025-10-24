# Metrics Documentation - V1.0

**Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Metrics Format**: Prometheus Text Format  
**Endpoint**: `GET /metrics`

---

## Overview

The V1.0 API exposes Prometheus-compatible metrics for monitoring application health, performance, and security posture. Metrics are accessible at the `/metrics` endpoint (unauthenticated for Prometheus scraper access).

### Metrics Architecture

```
Application → PromClientAdapter → /metrics endpoint → Prometheus → Grafana
```

- **Collection**: In-memory counters, gauges, histograms
- **Exposure**: Prometheus text format (OpenMetrics compatible)
- **Scraping**: Prometheus scrapes `/metrics` every 15s (configurable)
- **Visualization**: Grafana dashboards query Prometheus datasource
- **Retention**: 15 days (configurable in Prometheus)

---

## Available Metrics

### Application Health

#### `app_info`
**Type**: Gauge  
**Labels**: `version`, `environment`  
**Description**: Application version and environment information  
**Value**: Always 1  
**Example**:
```prometheus
app_info{version="1.0.0",environment="production"} 1
```

**Query Examples**:
```promql
# Check application version
app_info

# Count instances by version
count by (version) (app_info)
```

---

### Request Metrics

#### `http_requests_total`
**Type**: Counter  
**Labels**: `method`, `path`, `status`, `tenant_id`  
**Description**: Total HTTP requests received  
**Unit**: Requests

**Example**:
```prometheus
http_requests_total{method="GET",path="/api/v1/admin/users",status="200",tenant_id="tenant-123"} 1543
http_requests_total{method="POST",path="/api/v1/admin/tenants",status="201",tenant_id=""} 42
```

**Query Examples**:
```promql
# Total requests per minute
rate(http_requests_total[1m])

# Requests by status code
sum by (status) (rate(http_requests_total[5m]))

# 4xx error rate
sum(rate(http_requests_total{status=~"4.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Top 10 busiest endpoints
topk(10, sum by (path) (rate(http_requests_total[5m])))

# Tenant-specific request rate
sum by (tenant_id) (rate(http_requests_total{tenant_id!=""}[5m]))
```

---

#### `http_request_duration_seconds`
**Type**: Histogram  
**Labels**: `method`, `path`, `status`  
**Description**: HTTP request latency distribution  
**Unit**: Seconds  
**Buckets**: 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, +Inf

**Example**:
```prometheus
http_request_duration_seconds_bucket{method="GET",path="/api/v1/admin/users",status="200",le="0.1"} 1234
http_request_duration_seconds_bucket{method="GET",path="/api/v1/admin/users",status="200",le="+Inf"} 1543
http_request_duration_seconds_sum{method="GET",path="/api/v1/admin/users",status="200"} 123.45
http_request_duration_seconds_count{method="GET",path="/api/v1/admin/users",status="200"} 1543
```

**Query Examples**:
```promql
# p50 (median) latency
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# p95 latency (SLO: <200ms for CRUD)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Average request duration
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Slow endpoints (p95 > 500ms)
histogram_quantile(0.95, sum by (path) (rate(http_request_duration_seconds_bucket[5m]))) > 0.5
```

---

### Authentication & Authorization

#### `auth_login_attempts_total`
**Type**: Counter  
**Labels**: `status` (success, failed, rate_limited), `tenant_id`  
**Description**: Total login attempts  
**Unit**: Attempts

**Example**:
```prometheus
auth_login_attempts_total{status="success",tenant_id="tenant-123"} 4521
auth_login_attempts_total{status="failed",tenant_id="tenant-123"} 89
auth_login_attempts_total{status="rate_limited",tenant_id="tenant-456"} 12
```

**Query Examples**:
```promql
# Login success rate
sum(rate(auth_login_attempts_total{status="success"}[5m])) / sum(rate(auth_login_attempts_total[5m])) * 100

# Failed login rate (security alert if >10%)
sum(rate(auth_login_attempts_total{status="failed"}[5m])) / sum(rate(auth_login_attempts_total[5m])) * 100

# Rate-limited login attempts (potential brute force)
rate(auth_login_attempts_total{status="rate_limited"}[5m])

# Tenants with high failed login rates
topk(5, sum by (tenant_id) (rate(auth_login_attempts_total{status="failed"}[5m])))
```

---

#### `auth_token_refreshes_total`
**Type**: Counter  
**Labels**: `status` (success, failed, expired), `tenant_id`  
**Description**: Total token refresh attempts  
**Unit**: Refreshes

**Query Examples**:
```promql
# Token refresh rate
rate(auth_token_refreshes_total{status="success"}[5m])

# Expired token rate (high value = short-lived tokens expiring frequently)
rate(auth_token_refreshes_total{status="expired"}[5m])
```

---

### Database Metrics

#### `db_query_duration_seconds`
**Type**: Histogram  
**Labels**: `operation` (select, insert, update, delete), `table`  
**Description**: Database query execution time  
**Unit**: Seconds  
**Buckets**: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, +Inf

**Query Examples**:
```promql
# p95 query latency by table
histogram_quantile(0.95, sum by (table) (rate(db_query_duration_seconds_bucket[5m])))

# Slow queries (p95 > 100ms)
histogram_quantile(0.95, sum by (table, operation) (rate(db_query_duration_seconds_bucket[5m]))) > 0.1

# Query latency by operation type
histogram_quantile(0.95, sum by (operation) (rate(db_query_duration_seconds_bucket[5m])))
```

---

#### `db_connection_pool_size`
**Type**: Gauge  
**Labels**: `status` (idle, active, waiting)  
**Description**: Database connection pool statistics  
**Unit**: Connections

**Query Examples**:
```promql
# Current active connections
db_connection_pool_size{status="active"}

# Connection pool saturation
db_connection_pool_size{status="waiting"} / (db_connection_pool_size{status="active"} + db_connection_pool_size{status="idle"})

# Alert if connection pool near capacity
db_connection_pool_size{status="active"} / 20 > 0.8  # Assuming pool size = 20
```

---

### RBAC & Policy Engine

#### `policy_evaluations_total`
**Type**: Counter  
**Labels**: `decision` (ALLOW, DENY, ABSTAIN), `policy_name`, `tenant_id`  
**Description**: Total policy evaluations  
**Unit**: Evaluations

**Query Examples**:
```promql
# Policy evaluation rate
rate(policy_evaluations_total[5m])

# Deny rate (security metric)
sum(rate(policy_evaluations_total{decision="DENY"}[5m])) / sum(rate(policy_evaluations_total[5m])) * 100

# Top denying policies
topk(10, sum by (policy_name) (rate(policy_evaluations_total{decision="DENY"}[5m])))

# Tenant-specific policy denials
sum by (tenant_id) (rate(policy_evaluations_total{decision="DENY",tenant_id!=""}[5m]))
```

---

#### `policy_evaluation_duration_seconds`
**Type**: Histogram  
**Labels**: `policy_name`  
**Description**: Policy evaluation latency  
**Unit**: Seconds  
**Buckets**: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, +Inf

**Query Examples**:
```promql
# p95 policy evaluation latency
histogram_quantile(0.95, rate(policy_evaluation_duration_seconds_bucket[5m]))

# Slow policies (p95 > 50ms)
histogram_quantile(0.95, sum by (policy_name) (rate(policy_evaluation_duration_seconds_bucket[5m]))) > 0.05
```

---

### Multi-Tenancy

#### `active_users_gauge`
**Type**: Gauge  
**Labels**: `tenant_id`  
**Description**: Current number of active users per tenant  
**Unit**: Users

**Query Examples**:
```promql
# Total active users across all tenants
sum(active_users_gauge)

# Top 10 tenants by user count
topk(10, active_users_gauge)

# Tenants with 0 active users (churn candidates)
active_users_gauge == 0
```

---

#### `tenant_resource_usage`
**Type**: Gauge  
**Labels**: `tenant_id`, `resource_type` (users, policies, audit_events)  
**Description**: Resource consumption per tenant  
**Unit**: Count

**Query Examples**:
```promql
# Total policies per tenant
tenant_resource_usage{resource_type="policies"}

# Tenants exceeding resource limits
tenant_resource_usage{resource_type="users"} > 1000
```

---

### Rate Limiting (Deferred to Phase 2)

#### `rate_limit_hits_total`
**Type**: Counter  
**Labels**: `endpoint`, `tenant_id`, `limit_type` (per_user, per_tenant, global)  
**Description**: Total rate limit hits (throttled requests)  
**Unit**: Hits

**Query Examples**:
```promql
# Rate limit hit rate
rate(rate_limit_hits_total[5m])

# Tenants with high rate limit hits (potential abuse)
topk(10, sum by (tenant_id) (rate(rate_limit_hits_total[5m])))
```

---

## Admin Route Metrics (V1.0 Updates)

### New Admin Endpoints

The following admin endpoints have dedicated metrics in V1.0:

| Endpoint | Metric Path Label | Access |
|----------|------------------|--------|
| `GET /api/v1/admin/tenants` | `/api/v1/admin/tenants` | superadmin |
| `POST /api/v1/admin/tenants` | `/api/v1/admin/tenants` | superadmin |
| `GET /api/v1/admin/users` | `/api/v1/admin/users` | superadmin, tenant_admin |
| `POST /api/v1/admin/users` | `/api/v1/admin/users` | superadmin, tenant_admin |
| `GET /api/v1/admin/policies` | `/api/v1/admin/policies` | superadmin, tenant_admin |
| `GET /api/v1/admin/roles` | `/api/v1/admin/roles` | superadmin, tenant_admin |
| `POST /api/v1/admin/roles` | `/api/v1/admin/roles` | superadmin, tenant_admin |
| `POST /api/v1/admin/users/{id}/roles/{role_id}` | `/api/v1/admin/users/{id}/roles/{role_id}` | superadmin, tenant_admin |

**Admin Route Query Examples**:
```promql
# Admin endpoint usage
sum by (path) (rate(http_requests_total{path=~"/api/v1/admin/.*"}[5m]))

# Admin endpoint latency
histogram_quantile(0.95, sum by (path) (rate(http_request_duration_seconds_bucket{path=~"/api/v1/admin/.*"}[5m])))

# Admin 403 errors (unauthorized admin access attempts)
sum(rate(http_requests_total{path=~"/api/v1/admin/.*",status="403"}[5m]))
```

---

## Grafana Dashboard Examples

### Dashboard: API Performance

```promql
# Panel 1: Request Rate
sum(rate(http_requests_total[1m]))

# Panel 2: Error Rate
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100

# Panel 3: p95 Latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Panel 4: Top Slow Endpoints
topk(10, histogram_quantile(0.95, sum by (path) (rate(http_request_duration_seconds_bucket[5m]))))
```

### Dashboard: Security Monitoring

```promql
# Panel 1: Failed Login Rate
rate(auth_login_attempts_total{status="failed"}[5m])

# Panel 2: Policy Denials
rate(policy_evaluations_total{decision="DENY"}[5m])

# Panel 3: Rate Limit Hits
rate(rate_limit_hits_total[5m])

# Panel 4: Admin 403 Errors
rate(http_requests_total{path=~"/api/v1/admin/.*",status="403"}[5m])
```

### Dashboard: Multi-Tenant Health

```promql
# Panel 1: Active Users per Tenant
active_users_gauge

# Panel 2: Tenant Request Rate
sum by (tenant_id) (rate(http_requests_total{tenant_id!=""}[5m]))

# Panel 3: Tenant Error Rate
sum by (tenant_id) (rate(http_requests_total{tenant_id!="",status=~"5.."}[5m]))

# Panel 4: Top Tenants by Traffic
topk(10, sum by (tenant_id) (rate(http_requests_total{tenant_id!=""}[5m])))
```

---

## Alerting Rules

### Critical Alerts

```yaml
groups:
  - name: api_critical
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate (>5%)"
          description: "5xx error rate is {{ $value }}%"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "High API latency (p95 >1s)"
          description: "p95 latency is {{ $value }}s"

      - alert: DatabaseConnectionPoolExhausted
        expr: db_connection_pool_size{status="waiting"} > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool exhausted"
          description: "{{ $value }} connections waiting"
```

### Warning Alerts

```yaml
  - name: api_warning
    interval: 1m
    rules:
      - alert: HighFailedLoginRate
        expr: sum(rate(auth_login_attempts_total{status="failed"}[5m])) / sum(rate(auth_login_attempts_total[5m])) * 100 > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High failed login rate (>10%)"
          description: "Failed login rate is {{ $value }}%"

      - alert: SlowDatabaseQueries
        expr: histogram_quantile(0.95, sum by (table) (rate(db_query_duration_seconds_bucket[5m]))) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "Table {{ $labels.table }} p95 query time: {{ $value }}s"
```

---

## Metric Export Configuration

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'githubspeckit-api'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets:
          - 'localhost:8000'
          - 'api-1.prod.example.com:8000'
          - 'api-2.prod.example.com:8000'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
```

---

## Performance Benchmarks

Based on production-like load (1000 req/s, 100 tenants):

| Metric | Target | Current |
|--------|--------|---------|
| Request rate | - | 1000 req/s |
| p50 latency | <100ms | 45ms |
| p95 latency | <200ms | 120ms |
| p99 latency | <500ms | 280ms |
| Error rate | <1% | 0.3% |
| Policy evaluation p95 | <50ms | 18ms |
| DB query p95 | <50ms | 25ms |

---

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [OpenTelemetry Metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
- [V1.0 Logging Documentation](./LOGGING.md)
- [V1.0 API Routes](../README.md#api-endpoints)

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Maintainer**: Platform Team
