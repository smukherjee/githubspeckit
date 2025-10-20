#!/usr/bin/env bash
# SchemaSpy ERD Generation Wrapper Script
# Generates database documentation and ERD diagrams using SchemaSpy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TOOLS_DIR="${PROJECT_ROOT}/tools"
OUTPUT_DIR="${PROJECT_ROOT}/docs/schemaspy"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================"
echo "SchemaSpy ERD Generator"
echo "========================================"
echo ""

# Check for required tools
check_java() {
    if ! command -v java &> /dev/null; then
        echo -e "${RED}Error: Java is not installed${NC}"
        echo "Please install Java 11 or higher:"
        echo "  macOS: brew install openjdk@11"
        echo "  Linux: sudo apt-get install openjdk-11-jre"
        exit 1
    fi
    
    JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1)
    if [ "$JAVA_VERSION" -lt 11 ]; then
        echo -e "${RED}Error: Java 11 or higher is required${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Java $JAVA_VERSION detected${NC}"
}

# Download SchemaSpy if not present
download_schemaspy() {
    local SCHEMASPY_JAR="${TOOLS_DIR}/schemaspy.jar"
    local SCHEMASPY_VERSION="6.2.4"
    local SCHEMASPY_URL="https://github.com/schemaspy/schemaspy/releases/download/v${SCHEMASPY_VERSION}/schemaspy-${SCHEMASPY_VERSION}.jar"
    
    if [ -f "$SCHEMASPY_JAR" ]; then
        echo -e "${GREEN}✓ SchemaSpy JAR found${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Downloading SchemaSpy v${SCHEMASPY_VERSION}...${NC}"
    curl -L -o "$SCHEMASPY_JAR" "$SCHEMASPY_URL"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ SchemaSpy downloaded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to download SchemaSpy${NC}"
        exit 1
    fi
}

# Download PostgreSQL JDBC driver if not present
download_postgres_driver() {
    local DRIVER_JAR="${TOOLS_DIR}/postgresql.jar"
    local DRIVER_VERSION="42.7.1"
    local DRIVER_URL="https://jdbc.postgresql.org/download/postgresql-${DRIVER_VERSION}.jar"
    
    if [ -f "$DRIVER_JAR" ]; then
        echo -e "${GREEN}✓ PostgreSQL JDBC driver found${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Downloading PostgreSQL JDBC driver v${DRIVER_VERSION}...${NC}"
    curl -L -o "$DRIVER_JAR" "$DRIVER_URL"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL JDBC driver downloaded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to download PostgreSQL JDBC driver${NC}"
        exit 1
    fi
}

# Get database connection details
get_db_config() {
    # Try to load from .env file
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        source "${PROJECT_ROOT}/.env"
    fi
    
    # Parse DATABASE_URL or use defaults
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-infysight_users}"
    DB_USER="${DB_USER:-postgres}"
    DB_PASSWORD="${DB_PASSWORD:-postgres}"
    
    # If DATABASE_URL is set, parse it
    if [ -n "${DATABASE_URL:-}" ]; then
        # Extract components from postgresql://user:pass@host:port/dbname
        if [[ $DATABASE_URL =~ postgresql.*://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
            DB_USER="${BASH_REMATCH[1]}"
            DB_PASSWORD="${BASH_REMATCH[2]}"
            DB_HOST="${BASH_REMATCH[3]}"
            DB_PORT="${BASH_REMATCH[4]}"
            DB_NAME="${BASH_REMATCH[5]}"
        fi
    fi
    
    echo "Database configuration:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo ""
}

# Run SchemaSpy
run_schemaspy() {
    local SCHEMASPY_JAR="${TOOLS_DIR}/schemaspy.jar"
    local DRIVER_JAR="${TOOLS_DIR}/postgresql.jar"
    
    echo "Generating documentation..."
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Run SchemaSpy
    java -jar "$SCHEMASPY_JAR" \
        -t pgsql \
        -dp "$DRIVER_JAR" \
        -host "$DB_HOST" \
        -port "$DB_PORT" \
        -db "$DB_NAME" \
        -u "$DB_USER" \
        -p "$DB_PASSWORD" \
        -o "$OUTPUT_DIR" \
        -s public \
        -norows \
        -degree 2 \
        -renderer :cairo \
        -imageformat png
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ SchemaSpy documentation generated successfully${NC}"
        echo ""
        echo "Documentation location: $OUTPUT_DIR"
        echo "  - Open index.html in a browser to view"
        echo "  - ERD diagrams are in the diagrams/ subdirectory"
        echo ""
        echo "To view in browser:"
        echo "  open $OUTPUT_DIR/index.html"
    else
        echo -e "${RED}✗ SchemaSpy generation failed${NC}"
        exit 1
    fi
}

# Main execution
main() {
    check_java
    download_schemaspy
    download_postgres_driver
    get_db_config
    run_schemaspy
}

main "$@"
