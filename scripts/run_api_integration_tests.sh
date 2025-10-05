#!/usr/bin/env bash
#
# API Integration Test Runner
#
# This script sets up the test database, runs the integration test suite,
# and provides options for different test configurations.
#
# Usage:
#   ./scripts/run_api_integration_tests.sh [options]
#
# Options:
#   --clean     Drop and recreate test database before running tests
#   --verbose   Run tests with verbose output (-vv)
#   --coverage  Generate coverage report
#   --file FILE Run only tests from specific file
#   --class CLS Run only tests from specific class
#   --test NAME Run only specific test method
#   --help      Show this help message

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CLEAN_DB=false
VERBOSE=""
COVERAGE=false
TEST_FILTER=""
TEST_FILE=""
TEST_CLASS=""
TEST_METHOD=""

# Database configuration
DB_NAME="githubspeckit_test"
DB_USER="infysight_dbadmin"
DB_PASS="infysight_dbadmin123"
DB_HOST="localhost"
DB_PORT="5432"

export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_DB=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="-vv"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        --class)
            TEST_CLASS="$2"
            shift 2
            ;;
        --test)
            TEST_METHOD="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --clean      Drop and recreate test database"
            echo "  --verbose    Run tests with verbose output"
            echo "  --coverage   Generate coverage report"
            echo "  --file FILE  Run only tests from specific file"
            echo "  --class CLS  Run only tests from specific class"
            echo "  --test NAME  Run only specific test method"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to print colored messages
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# Function to check if PostgreSQL is running
check_postgres() {
    print_msg "$BLUE" "🔍 Checking PostgreSQL connection..."
    export PGPASSWORD="$DB_PASS"
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        print_msg "$RED" "❌ Cannot connect to PostgreSQL server"
        print_msg "$YELLOW" "   Please ensure PostgreSQL is running and credentials are correct"
        unset PGPASSWORD
        exit 1
    fi
    unset PGPASSWORD
    print_msg "$GREEN" "✅ PostgreSQL is running"
}

# Function to create/recreate test database
setup_database() {
    export PGPASSWORD="$DB_PASS"
    
    if [ "$CLEAN_DB" = true ]; then
        print_msg "$BLUE" "🧹 Dropping existing test database..."
        dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME" 2>/dev/null || true
        
        print_msg "$BLUE" "🏗️  Creating fresh test database..."
        if ! createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null; then
            print_msg "$RED" "❌ Failed to create database. User may not have CREATEDB permission."
            print_msg "$YELLOW" "   Run as superuser: psql -c \"ALTER USER $DB_USER CREATEDB;\""
            unset PGPASSWORD
            exit 1
        fi
        print_msg "$GREEN" "✅ Test database created"
    else
        # Check if database exists
        if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
            print_msg "$YELLOW" "⚠️  Test database does not exist, creating..."
            if ! createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null; then
                print_msg "$RED" "❌ Failed to create database. User may not have CREATEDB permission."
                print_msg "$YELLOW" "   Run as superuser: psql -c \"ALTER USER $DB_USER CREATEDB;\""
                unset PGPASSWORD
                exit 1
            fi
            print_msg "$GREEN" "✅ Test database created"
        else
            print_msg "$GREEN" "✅ Test database exists"
        fi
    fi
    
    unset PGPASSWORD
}

# Function to run migrations
run_migrations() {
    print_msg "$BLUE" "🔄 Running database migrations..."
    
    # Change to project root directory for Alembic
    cd "$(dirname "$0")/.."
    
    # Run migrations with DATABASE_URL set
    DATABASE_URL="$DATABASE_URL" alembic upgrade head
    
    if [ $? -ne 0 ]; then
        print_msg "$RED" "❌ Migration failed"
        exit 1
    fi
    
    print_msg "$GREEN" "✅ Migrations complete"
}

# Function to activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        print_msg "$BLUE" "🐍 Activating virtual environment..."
        source .venv/bin/activate
        print_msg "$GREEN" "✅ Virtual environment activated"
    elif [ -d "venv" ]; then
        print_msg "$BLUE" "🐍 Activating virtual environment..."
        source venv/bin/activate
        print_msg "$GREEN" "✅ Virtual environment activated"
    else
        print_msg "$YELLOW" "⚠️  No virtual environment found, using system Python"
    fi
}

# Function to build pytest command
build_pytest_cmd() {
    local cmd="pytest tests/api/integration/"
    
    # Add file filter
    if [ -n "$TEST_FILE" ]; then
        cmd="pytest tests/api/integration/${TEST_FILE}"
    fi
    
    # Add class filter
    if [ -n "$TEST_CLASS" ]; then
        cmd="${cmd}::${TEST_CLASS}"
    fi
    
    # Add method filter
    if [ -n "$TEST_METHOD" ]; then
        cmd="${cmd}::${TEST_METHOD}"
    fi
    
    # Add verbose flag
    if [ -n "$VERBOSE" ]; then
        cmd="${cmd} ${VERBOSE}"
    fi
    
    # Add coverage
    if [ "$COVERAGE" = true ]; then
        cmd="${cmd} --cov=src/adapters/api --cov-report=html --cov-report=term-missing"
    fi
    
    echo "$cmd"
}

# Main execution
main() {
    print_msg "$BLUE" "╔════════════════════════════════════════════════════╗"
    print_msg "$BLUE" "║  API Integration Test Suite                       ║"
    print_msg "$BLUE" "╚════════════════════════════════════════════════════╝"
    echo ""
    
    # Change to project root directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    cd "$PROJECT_ROOT"
    
    print_msg "$BLUE" "📁 Project root: $PROJECT_ROOT"
    echo ""
    
    # Step 1: Check PostgreSQL
    check_postgres
    echo ""
    
    # Step 2: Setup database
    setup_database
    echo ""
    
    # Step 3: Activate virtual environment (before migrations)
    activate_venv
    echo ""
    
    # Step 4: Run migrations
    run_migrations
    echo ""
    
    # Step 5: Run tests
    local pytest_cmd=$(build_pytest_cmd)
    print_msg "$BLUE" "🧪 Running tests..."
    print_msg "$YELLOW" "   Command: $pytest_cmd"
    echo ""
    
    # Ensure we're in project root for pytest
    cd "$PROJECT_ROOT"
    
    # Run pytest and capture exit code
    set +e
    eval "$pytest_cmd"
    local exit_code=$?
    set -e
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        print_msg "$GREEN" "╔════════════════════════════════════════════════════╗"
        print_msg "$GREEN" "║  ✅ ALL TESTS PASSED!                              ║"
        print_msg "$GREEN" "╚════════════════════════════════════════════════════╝"
        
        if [ "$COVERAGE" = true ]; then
            print_msg "$BLUE" "📊 Coverage report generated: htmlcov/index.html"
        fi
    else
        print_msg "$RED" "╔════════════════════════════════════════════════════╗"
        print_msg "$RED" "║  ❌ TESTS FAILED                                   ║"
        print_msg "$RED" "╚════════════════════════════════════════════════════╝"
    fi
    
    exit $exit_code
}

# Run main function
main
