#!/usr/bin/env bash

# Test Script for T055: Native Bootstrap Validation
# 
# Purpose: Validate that `make bootstrap` completes in <5 minutes on a clean environment
# Target: Fresh macOS/Linux system without project dependencies
# 
# Prerequisites:
#   - Python 3.12+ installed
#   - PostgreSQL 15+ installed and running
#   - Git installed
#   - No existing .venv or infysight_users database
#
# Usage:
#   ./scripts/test_native_bootstrap.sh
#
# Exit Codes:
#   0 - Success (bootstrap completed in <5 minutes)
#   1 - Failure (errors or timeout exceeded)

set -e

# Configuration
BOOTSTRAP_TIMEOUT_SECONDS=300  # 5 minutes
REPO_URL="https://github.com/sujoymukherjee-corp/githubspeckit.git"
TEST_DIR="/tmp/githubspeckit-bootstrap-test-$(date +%s)"
LOG_FILE="/tmp/bootstrap-test-$(date +%s).log"

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
    log_info "Cleaning up test environment..."
    if [[ -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR"
    fi
    
    # Drop test database if created
    if command -v psql &> /dev/null; then
        psql -U postgres -c "DROP DATABASE IF EXISTS infysight_users;" 2>/dev/null || true
    fi
}

# Trap cleanup on exit
trap cleanup EXIT

# Main test execution
main() {
    log_info "Starting T055: Native Bootstrap Validation Test"
    log_info "Log file: $LOG_FILE"
    log_info "Timeout: ${BOOTSTRAP_TIMEOUT_SECONDS}s (5 minutes)"
    echo ""
    
    # Step 1: Check prerequisites
    log_info "Step 1/6: Checking prerequisites..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.12+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python version: $PYTHON_VERSION"
    
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL client not found. Please install PostgreSQL 15+"
        exit 1
    fi
    
    PG_VERSION=$(psql --version | cut -d' ' -f3)
    log_success "PostgreSQL version: $PG_VERSION"
    
    if ! command -v git &> /dev/null; then
        log_error "Git not found. Please install Git"
        exit 1
    fi
    
    log_success "All prerequisites met"
    echo ""
    
    # Step 2: Clone repository
    log_info "Step 2/6: Cloning repository to $TEST_DIR..."
    START_CLONE=$(date +%s)
    
    git clone --branch 012-v1-cleanup-legacy-removal "$REPO_URL" "$TEST_DIR" >> "$LOG_FILE" 2>&1
    
    END_CLONE=$(date +%s)
    CLONE_DURATION=$((END_CLONE - START_CLONE))
    log_success "Repository cloned in ${CLONE_DURATION}s"
    echo ""
    
    # Step 3: Navigate to directory
    cd "$TEST_DIR"
    log_info "Step 3/6: Working directory: $(pwd)"
    echo ""
    
    # Step 4: Run make bootstrap with timeout
    log_info "Step 4/6: Running 'make bootstrap' (timeout: ${BOOTSTRAP_TIMEOUT_SECONDS}s)..."
    START_BOOTSTRAP=$(date +%s)
    
    if timeout ${BOOTSTRAP_TIMEOUT_SECONDS}s make bootstrap >> "$LOG_FILE" 2>&1; then
        END_BOOTSTRAP=$(date +%s)
        BOOTSTRAP_DURATION=$((END_BOOTSTRAP - START_BOOTSTRAP))
        
        if [[ $BOOTSTRAP_DURATION -lt $BOOTSTRAP_TIMEOUT_SECONDS ]]; then
            log_success "Bootstrap completed in ${BOOTSTRAP_DURATION}s (under 5 minute target)"
        else
            log_error "Bootstrap took ${BOOTSTRAP_DURATION}s (exceeded 5 minute target)"
            exit 1
        fi
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 124 ]]; then
            log_error "Bootstrap timed out after ${BOOTSTRAP_TIMEOUT_SECONDS}s"
        else
            log_error "Bootstrap failed with exit code $EXIT_CODE"
        fi
        log_info "Check log file for details: $LOG_FILE"
        exit 1
    fi
    echo ""
    
    # Step 5: Verify health endpoint
    log_info "Step 5/6: Verifying API health endpoint..."
    
    # Wait for server to start
    sleep 3
    
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
    
    if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
        VERSION=$(echo "$HEALTH_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        log_success "Health check passed (version: $VERSION)"
    else
        log_error "Health check failed. Response: $HEALTH_RESPONSE"
        exit 1
    fi
    echo ""
    
    # Step 6: Verify database seeding
    log_info "Step 6/6: Verifying database seeding..."
    
    TENANT_COUNT=$(psql -U postgres -d infysight_users -t -c "SELECT COUNT(*) FROM tenants;" 2>/dev/null || echo "0")
    USER_COUNT=$(psql -U postgres -d infysight_users -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    
    TENANT_COUNT=$(echo "$TENANT_COUNT" | xargs)
    USER_COUNT=$(echo "$USER_COUNT" | xargs)
    
    if [[ "$TENANT_COUNT" -gt 0 && "$USER_COUNT" -gt 0 ]]; then
        log_success "Database seeded: $TENANT_COUNT tenant(s), $USER_COUNT user(s)"
    else
        log_error "Database seeding incomplete: $TENANT_COUNT tenant(s), $USER_COUNT user(s)"
        exit 1
    fi
    echo ""
    
    # Final summary
    TOTAL_DURATION=$((END_BOOTSTRAP - START_CLONE))
    echo "═══════════════════════════════════════════════════════"
    log_success "T055 VALIDATION PASSED"
    echo "═══════════════════════════════════════════════════════"
    echo "  Clone:     ${CLONE_DURATION}s"
    echo "  Bootstrap: ${BOOTSTRAP_DURATION}s"
    echo "  Total:     ${TOTAL_DURATION}s"
    echo "  Target:    <300s (5 minutes)"
    echo ""
    echo "  ✅ All prerequisites met"
    echo "  ✅ Repository cloned successfully"
    echo "  ✅ Bootstrap completed under time limit"
    echo "  ✅ Health endpoint responding"
    echo "  ✅ Database seeded with test data"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    log_info "Full logs: $LOG_FILE"
}

# Execute main function
main
