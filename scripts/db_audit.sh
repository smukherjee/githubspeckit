#!/usr/bin/env bash
# Database Audit Orchestration Script
# Executes orphan tables, missing indexes, and sensitive column checks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Database Audit Tool"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Attempting to activate .venv..."
    if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
        source "${PROJECT_ROOT}/.venv/bin/activate"
    else
        echo -e "${RED}Error: Virtual environment not found${NC}"
        exit 1
    fi
fi

# Ensure we're in the project root
cd "${PROJECT_ROOT}"

# Check if Python scripts exist
SCRIPTS=(
    "scripts/detect_orphaned_tables.py"
    "scripts/analyze_missing_indexes.py"
    "scripts/check_sensitive_columns.py"
)

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "${script}" ]; then
        echo -e "${RED}Error: ${script} not found${NC}"
        exit 1
    fi
done

# Create output directory
OUTPUT_DIR="${PROJECT_ROOT}/reports/db-audit"
mkdir -p "${OUTPUT_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${OUTPUT_DIR}/audit_${TIMESTAMP}.txt"

echo "Output directory: ${OUTPUT_DIR}"
echo "Report file: ${REPORT_FILE}"
echo ""

# Function to run a script and capture output
run_audit() {
    local script=$1
    local description=$2
    
    echo -e "${GREEN}Running: ${description}${NC}"
    echo "==========================================" | tee -a "${REPORT_FILE}"
    echo "${description}" | tee -a "${REPORT_FILE}"
    echo "Timestamp: $(date)" | tee -a "${REPORT_FILE}"
    echo "==========================================" | tee -a "${REPORT_FILE}"
    
    if python "${script}" | tee -a "${REPORT_FILE}"; then
        echo -e "${GREEN}✓ ${description} completed successfully${NC}"
    else
        echo -e "${RED}✗ ${description} failed${NC}"
        exit 1
    fi
    
    echo "" | tee -a "${REPORT_FILE}"
}

# Run audits
run_audit "scripts/detect_orphaned_tables.py" "Orphaned Tables Detection"
run_audit "scripts/analyze_missing_indexes.py" "Missing Indexes Analysis"
run_audit "scripts/check_sensitive_columns.py" "Sensitive Columns Check"

# Summary
echo "==========================================" | tee -a "${REPORT_FILE}"
echo "Database Audit Summary" | tee -a "${REPORT_FILE}"
echo "==========================================" | tee -a "${REPORT_FILE}"
echo "All audits completed successfully" | tee -a "${REPORT_FILE}"
echo "Full report: ${REPORT_FILE}" | tee -a "${REPORT_FILE}"
echo ""
echo -e "${GREEN}✓ Database audit completed successfully${NC}"
echo "Report saved to: ${REPORT_FILE}"
