# Docker Setup Guide - GitHubSpecKit

## Quick Start

```bash
# Build and start all services
make docker-up

# View API logs
make docker-logs

# Stop all services
make docker-down

# Clean reset (removes volumes)
make docker-reset
```

## Services

### 1. PostgreSQL Database
- **Port**: 5432
- **Database**: infysight_users
- **User**: postgres
- **Password**: postgres
- **Health Check**: `pg_isready` every 5s

### 2. Redis Cache
- **Port**: 6379
- **Persistence**: AOF enabled
- **Health Check**: `redis-cli ping` every 5s

### 3. pgAdmin (Database UI)
- **Port**: 5050
- **URL**: http://localhost:5050
- **Email**: admin@example.com
- **Password**: admin

### 4. FastAPI Application
- **Port**: 8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Entrypoint**: Runs migrations, seeds DB (optional), starts API

## Environment Variables

Set in `docker-compose.yml` under `api` service:

```yaml
# Database
DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/infysight_users

# Redis
REDIS_URL: redis://redis:6379/0

# JWT
JWT_SECRET_KEY: dev-secret-key-change-in-production
JWT_ALGORITHM: HS256
JWT_EXPIRATION_MINUTES: 60

# Rate Limiting
RATE_LIMIT_USER_CREATION: 100

# Optional: Auto-seed database on startup
SEED_DATABASE: "true"
SEED_TENANT_SLUG: "primary"
SEED_ADMIN_EMAIL: "admin@example.com"
```

## Development Workflow

### First Time Setup

```bash
# Build images
make docker-build

# Start services
make docker-up

# Check status
docker-compose ps

# Expected output:
# NAME                       STATUS              PORTS
# githubspeckit-api          Up (healthy)        0.0.0.0:8000->8000/tcp
# githubspeckit-postgres     Up (healthy)        0.0.0.0:5432->5432/tcp
# githubspeckit-redis        Up (healthy)        0.0.0.0:6379->6379/tcp
# githubspeckit-pgadmin      Up                  0.0.0.0:5050->80/tcp
```

### View Logs

```bash
# All services
docker-compose logs -f

# Just API
make docker-logs

# Just PostgreSQL
docker-compose logs -f postgres

# Just Redis
docker-compose logs -f redis
```

### Exec into Containers

```bash
# API container
docker exec -it githubspeckit-api bash

# PostgreSQL
docker exec -it githubspeckit-postgres psql -U postgres -d infysight_users

# Redis
docker exec -it githubspeckit-redis redis-cli
```

### Database Operations

```bash
# Run migrations manually
docker exec githubspeckit-api alembic upgrade head

# Seed database manually
docker exec githubspeckit-api python -m cli.db_bootstrap \
  --tenant-slug=acme \
  --admin-email=admin@acme.com

# Connect to database
docker exec -it githubspeckit-postgres psql -U postgres -d infysight_users
```

### Reset Everything

```bash
# Stop and remove all containers + volumes (DESTRUCTIVE)
make docker-clean

# Rebuild and start fresh
make docker-reset
```

## Troubleshooting

### API Container Won't Start

**Check logs**:
```bash
docker-compose logs api
```

**Common issues**:
1. **Database not ready**: Entrypoint waits for PostgreSQL, check `pg_isready` logs
2. **Migration failure**: Check alembic logs in API container output
3. **Import errors**: Ensure `PYTHONPATH=/app/src` is set in Dockerfile

**Solution**: Check entrypoint script output for errors

### Health Check Failing

**Check endpoint**:
```bash
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy"}
```

**Verify container is running**:
```bash
docker-compose ps
```

### Port Already in Use

**Find process using port**:
```bash
lsof -i :8000  # API
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

**Kill process**:
```bash
kill -9 <PID>
```

### Database Connection Errors

**Verify PostgreSQL is healthy**:
```bash
docker-compose ps postgres

# Should show: Up (healthy)
```

**Test connection from API container**:
```bash
docker exec githubspeckit-api pg_isready -h postgres -U postgres
```

### Redis Connection Errors

**Verify Redis is healthy**:
```bash
docker exec githubspeckit-redis redis-cli ping
# Should return: PONG
```

## File Structure

```
.
├── Dockerfile              # Multi-stage build for API
├── docker-compose.yml      # Service orchestration
├── docker-entrypoint.sh    # API startup script
├── .dockerignore          # Build optimization
├── src/                   # Application code (mounted in dev)
├── alembic/               # Database migrations
└── config/                # Configuration files
```

## Performance Tips

### Development Mode
- Source code is mounted as read-only volumes for hot reload
- Build time: ~2-3 minutes (first time)
- Startup time: ~10-15 seconds

### Production Mode
- Remove volume mounts from `docker-compose.yml`
- Use `--build-arg` for production secrets
- Enable `restart: always` for auto-recovery

## Security Notes

1. **Change default passwords** in production
2. **Use environment-specific secrets** (not hardcoded in docker-compose.yml)
3. **Non-root user**: API runs as `appuser` (UID 1000)
4. **Network isolation**: All services on `githubspeckit-net` bridge network

## Monitoring

### Container Stats
```bash
docker stats githubspeckit-api githubspeckit-postgres githubspeckit-redis
```

### Health Status
```bash
# Check all health checks
docker-compose ps

# Detailed inspect
docker inspect --format='{{.State.Health.Status}}' githubspeckit-api
```

## Next Steps After Setup

1. ✅ Verify all containers are healthy: `docker-compose ps`
2. ✅ Access API docs: http://localhost:8000/docs
3. ✅ Access pgAdmin: http://localhost:5050
4. ✅ Run test suite: Make sure local tests still pass
5. ✅ Deploy to production: Adapt docker-compose.yml for your environment

---

**Need help?** Check container logs: `docker-compose logs -f api`
