#!/usr/bin/env bash

# Test Script for T056: Docker Environment Validation
#
# Purpose: Validate that `make docker-up` creates a working environment
# Target: Clean Linux/macOS system with Docker installed
#
# Prerequisites:
#   - Docker 20+ installed and running
#   - Docker Compose v2+ installed
#   - No existing githubspeckit containers/volumes
#
# Usage:
#   ./scripts/test_docker_environment.sh
#
# Exit Codes:
#   0 - Success (all services healthy)
#   1 - Failure (errors or services unhealthy)

set -e

# Configuration
STARTUP_TIMEOUT_SECONDS=120  # 2 minutes for all services
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_INTERVAL=3
LOG_FILE="/tmp/docker-env-test-$(date +%s).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up Docker environment..."
    make docker-down >> "$LOG_FILE" 2>&1 || true
    docker volume prune -f >> "$LOG_FILE" 2>&1 || true
}

# Trap cleanup on exit
trap cleanup EXIT

# Main test execution
main() {
    log_info "Starting T056: Docker Environment Validation Test"
    log_info "Log file: $LOG_FILE"
    echo ""
    
    # Step 1: Check prerequisites
    log_info "Step 1/7: Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker 20+"
        exit 1
    fi
    
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    log_success "Docker version: $DOCKER_VERSION"
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not found. Please install Docker Compose v2+"
        exit 1
    fi
    
    COMPOSE_VERSION=$(docker compose version --short)
    log_success "Docker Compose version: $COMPOSE_VERSION"
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon not running. Please start Docker"
        exit 1
    fi
    
    log_success "Docker daemon is running"
    echo ""
    
    # Step 2: Verify project structure
    log_info "Step 2/7: Verifying project structure..."
    
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Run from project root"
        exit 1
    fi
    
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile not found. Run from project root"
        exit 1
    fi
    
    if [[ ! -f "Makefile" ]]; then
        log_error "Makefile not found. Run from project root"
        exit 1
    fi
    
    log_success "Project structure verified"
    echo ""
    
    # Step 3: Start Docker environment
    log_info "Step 3/7: Starting Docker environment (make docker-up)..."
    START_TIME=$(date +%s)
    
    if timeout ${STARTUP_TIMEOUT_SECONDS}s make docker-up >> "$LOG_FILE" 2>&1; then
        END_TIME=$(date +%s)
        STARTUP_DURATION=$((END_TIME - START_TIME))
        log_success "Docker environment started in ${STARTUP_DURATION}s"
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 124 ]]; then
            log_error "Docker startup timed out after ${STARTUP_TIMEOUT_SECONDS}s"
        else
            log_error "Docker startup failed with exit code $EXIT_CODE"
        fi
        log_info "Check log file for details: $LOG_FILE"
        exit 1
    fi
    echo ""
    
    # Step 4: Verify all services are running
    log_info "Step 4/7: Verifying all services are running..."
    
    EXPECTED_SERVICES=("postgres" "redis" "pgadmin" "api")
    
    for service in "${EXPECTED_SERVICES[@]}"; do
        if docker compose ps "$service" | grep -q "Up"; then
            log_success "Service '$service' is running"
        else
            log_error "Service '$service' is not running"
            docker compose ps "$service"
            exit 1
        fi
    done
    echo ""
    
    # Step 5: Check PostgreSQL health
    log_info "Step 5/7: Checking PostgreSQL health..."
    
    PG_CONTAINER=$(docker compose ps -q postgres)
    if docker exec "$PG_CONTAINER" pg_isready -U postgres &> /dev/null; then
        log_success "PostgreSQL is accepting connections"
    else
        log_error "PostgreSQL health check failed"
        exit 1
    fi
    
    # Verify database exists
    DB_EXISTS=$(docker exec "$PG_CONTAINER" psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='infysight_users'" 2>/dev/null || echo "0")
    if [[ "$DB_EXISTS" == "1" ]]; then
        log_success "Database 'infysight_users' exists"
    else
        log_warning "Database 'infysight_users' not found (may need manual creation)"
    fi
    echo ""
    
    # Step 6: Check Redis health
    log_info "Step 6/7: Checking Redis health..."
    
    REDIS_CONTAINER=$(docker compose ps -q redis)
    if docker exec "$REDIS_CONTAINER" redis-cli ping 2>&1 | grep -q "PONG"; then
        log_success "Redis is responding"
    else
        log_error "Redis health check failed"
        exit 1
    fi
    echo ""
    
    # Step 7: Check API health endpoint
    log_info "Step 7/7: Checking API health endpoint..."
    
    # Wait for API to be ready
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        log_info "Attempt $i/$HEALTH_CHECK_RETRIES: Checking http://localhost:8000/health"
        
        HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
        
        if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
            VERSION=$(echo "$HEALTH_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
            log_success "API health check passed (version: $VERSION)"
            break
        else
            if [[ $i -eq $HEALTH_CHECK_RETRIES ]]; then
                log_error "API health check failed after $HEALTH_CHECK_RETRIES attempts"
                log_error "Response: $HEALTH_RESPONSE"
                exit 1
            fi
            sleep $HEALTH_CHECK_INTERVAL
        fi
    done
    echo ""
    
    # Step 8: Verify admin routes
    log_info "Step 8/7: Verifying admin routes (401 without auth)..."
    
    ADMIN_TENANTS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/admin/tenants 2>/dev/null)
    
    if [[ "$ADMIN_TENANTS" == "401" ]]; then
        log_success "Admin tenants route requires authentication (expected 401)"
    else
        log_error "Admin tenants route returned unexpected status: $ADMIN_TENANTS"
        exit 1
    fi
    echo ""
    
    # Final summary
    echo "═══════════════════════════════════════════════════════"
    log_success "T056 VALIDATION PASSED"
    echo "═══════════════════════════════════════════════════════"
    echo "  Startup:   ${STARTUP_DURATION}s"
    echo "  Target:    <120s (2 minutes)"
    echo ""
    echo "  ✅ Docker prerequisites met"
    echo "  ✅ All 4 services running (postgres, redis, pgadmin, api)"
    echo "  ✅ PostgreSQL accepting connections"
    echo "  ✅ Redis responding to PING"
    echo "  ✅ API health endpoint responding"
    echo "  ✅ Admin routes require authentication"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    log_info "Services running. Use 'make docker-logs' to view logs"
    log_info "Use 'make docker-down' to stop services"
    log_info "Full logs: $LOG_FILE"
}

# Execute main function
main
