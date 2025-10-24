#!/usr/bin/env bash
#
# OWASP ZAP Security Scanner Script
# 
# Provides automated security scanning with multiple scan types and options.
# Follows OWASP best practices and integrates with CI/CD pipelines.
#
# Usage:
#   ./scripts/security/run-zap-scan.sh [SCAN_TYPE] [OPTIONS]
#
# Scan Types:
#   baseline    - Quick passive scan (safe for production)
#   api         - API-specific scan using OpenAPI spec
#   full        - Full active scan (WARNING: modifies data, test DB only)
#   authenticated - Authenticated scan with JWT token
#   all         - Run all scan types sequentially
#
# Options:
#   -t, --target URL          Target URL (default: http://localhost:8000)
#   -o, --output DIR          Output directory (default: reports/security/zap)
#   -f, --format FORMAT       Report format: html,json,md,xml (default: html,json,md)
#   -c, --config FILE         ZAP config file for rules
#   -a, --auth-token TOKEN    JWT token for authenticated scans
#   -s, --safe                Run in safe mode (no active attacks)
#   -v, --verbose             Verbose output
#   -h, --help                Show this help message
#
# Examples:
#   # Quick baseline scan
#   ./scripts/security/run-zap-scan.sh baseline
#
#   # API scan with custom target
#   ./scripts/security/run-zap-scan.sh api --target http://staging.example.com
#
#   # Full active scan (test environment only!)
#   ./scripts/security/run-zap-scan.sh full --target http://test.local:8000
#
#   # Authenticated scan with JWT
#   ./scripts/security/run-zap-scan.sh authenticated --auth-token "eyJ..."
#
#   # All scans with custom output
#   ./scripts/security/run-zap-scan.sh all --output /tmp/zap-results

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
SCAN_TYPE="${1:-baseline}"
TARGET_URL="http://localhost:8000"
OUTPUT_DIR="reports/security/zap"
REPORT_FORMATS="html,json,md"
CONFIG_FILE=""
AUTH_TOKEN=""
SAFE_MODE=false
VERBOSE=false
ZAP_IMAGE="ghcr.io/zaproxy/zaproxy:stable"
OPENAPI_ENDPOINT="/openapi.json"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*"
    fi
}

# Help message
show_help() {
    cat << EOF
OWASP ZAP Security Scanner

Usage: $(basename "$0") [SCAN_TYPE] [OPTIONS]

Scan Types:
  baseline           Quick passive scan (safe for production)
  api                API-specific scan using OpenAPI spec
  full               Full active scan (WARNING: modifies data)
  authenticated      Authenticated scan with JWT token
  all                Run all scan types sequentially

Options:
  -t, --target URL          Target URL (default: http://localhost:8000)
  -o, --output DIR          Output directory (default: reports/security/zap)
  -f, --format FORMAT       Report format: html,json,md,xml (default: html,json,md)
  -c, --config FILE         ZAP config file for custom rules
  -a, --auth-token TOKEN    JWT token for authenticated scans
  -s, --safe                Run in safe mode (no active attacks)
  -v, --verbose             Verbose output
  -h, --help                Show this help message

Examples:
  # Quick baseline scan
  $(basename "$0") baseline

  # API scan with custom target
  $(basename "$0") api --target http://staging.example.com

  # Full active scan (test environment only!)
  $(basename "$0") full --target http://test.local:8000 --safe

  # Authenticated scan with JWT
  $(basename "$0") authenticated --auth-token "eyJ..."

  # All scans with verbose output
  $(basename "$0") all --verbose

Security Notes:
  - Baseline scans are safe for production (passive only)
  - API scans import OpenAPI spec from /openapi.json
  - Full scans send active attacks (use test DB only!)
  - Authenticated scans test RBAC and authorization

EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    # Shift past scan type
    shift || true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--target)
                TARGET_URL="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -f|--format)
                REPORT_FORMATS="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -a|--auth-token)
                AUTH_TOKEN="$2"
                shift 2
                ;;
            -s|--safe)
                SAFE_MODE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Run '$(basename "$0") --help' for usage information"
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    # Check if ZAP image exists, pull if not
    if ! docker images | grep -q "zaproxy/zaproxy"; then
        log_info "Pulling OWASP ZAP Docker image..."
        docker pull "$ZAP_IMAGE"
    fi
    
    # Check target accessibility
    log_verbose "Checking target URL accessibility: $TARGET_URL"
    if ! curl -s -f -o /dev/null --max-time 5 "${TARGET_URL}/health" 2>/dev/null; then
        log_warning "Target URL health check failed: ${TARGET_URL}/health"
        log_warning "Scans may fail if the server is not running."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Prerequisites validated"
}

# Setup output directory
setup_output_dir() {
    log_info "Setting up output directory: $OUTPUT_DIR"
    
    # Convert to absolute path if relative
    if [[ ! "$OUTPUT_DIR" = /* ]]; then
        OUTPUT_DIR="$(cd "$REPO_ROOT" && pwd)/$OUTPUT_DIR"
    fi
    
    log_verbose "Absolute output path: $OUTPUT_DIR"
    
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"
    
    # Create timestamp for this scan run
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RUN_DIR="${OUTPUT_DIR}/run_${TIMESTAMP}"
    mkdir -p "$RUN_DIR"
    
    log_verbose "Scan results will be saved to: $RUN_DIR"
}

# Download and prepare OpenAPI spec
prepare_openapi_spec() {
    log_info "Downloading OpenAPI specification..."
    
    local openapi_url="${TARGET_URL}${OPENAPI_ENDPOINT}"
    local openapi_file="${RUN_DIR}/openapi.json"
    local openapi_with_server="${RUN_DIR}/openapi-with-server.json"
    
    # Download OpenAPI spec
    if ! curl -s -f -o "$openapi_file" "$openapi_url"; then
        log_error "Failed to download OpenAPI spec from: $openapi_url"
        return 1
    fi
    
    # Add server URL to OpenAPI spec for ZAP import
    # Convert localhost to host.docker.internal for Docker networking
    local docker_target="${TARGET_URL/localhost/host.docker.internal}"
    
    if command -v jq &> /dev/null; then
        jq ". + {servers: [{url: \"$docker_target\"}]}" "$openapi_file" > "$openapi_with_server"
        log_success "OpenAPI spec prepared with server URL: $docker_target"
        echo "$openapi_with_server"
    else
        log_warning "jq not found. OpenAPI spec may not work with ZAP."
        echo "$openapi_file"
    fi
}

# Generate report file paths
generate_report_paths() {
    local scan_name="$1"
    # Use relative path for Docker container (relative to /zap/wrk mount point)
    local run_dirname=$(basename "$RUN_DIR")
    local base_name="${run_dirname}/${scan_name}-report"
    
    REPORT_ARGS=""
    
    if [[ "$REPORT_FORMATS" == *"html"* ]]; then
        REPORT_ARGS="$REPORT_ARGS -r ${base_name}.html"
    fi
    
    if [[ "$REPORT_FORMATS" == *"json"* ]]; then
        REPORT_ARGS="$REPORT_ARGS -J ${base_name}.json"
    fi
    
    if [[ "$REPORT_FORMATS" == *"md"* ]]; then
        REPORT_ARGS="$REPORT_ARGS -w ${base_name}.md"
    fi
    
    if [[ "$REPORT_FORMATS" == *"xml"* ]]; then
        REPORT_ARGS="$REPORT_ARGS -x ${base_name}.xml"
    fi
    
    echo "$REPORT_ARGS"
}

# Run baseline scan
run_baseline_scan() {
    log_info "Starting OWASP ZAP Baseline Scan..."
    log_info "Target: $TARGET_URL"
    log_info "Mode: Passive (safe for production)"
    
    local docker_target="${TARGET_URL/localhost/host.docker.internal}"
    local report_args
    report_args=$(generate_report_paths "baseline")
    
    # Build ZAP command
    local zap_cmd="zap-baseline.py -t ${docker_target}/api/v1/ $report_args"
    
    if [ -n "$CONFIG_FILE" ]; then
        zap_cmd="$zap_cmd -c /zap/wrk/$(basename "$CONFIG_FILE")"
    fi
    
    if [ "$VERBOSE" = true ]; then
        zap_cmd="$zap_cmd -d"
    fi
    
    log_verbose "ZAP command: $zap_cmd"
    
    # Run ZAP baseline scan
    local exit_code=0
    docker run --rm \
        -v "${OUTPUT_DIR}:/zap/wrk:rw" \
        ${CONFIG_FILE:+-v "${CONFIG_FILE}:/zap/wrk/$(basename "$CONFIG_FILE"):ro"} \
        "$ZAP_IMAGE" \
        $zap_cmd || exit_code=$?
    
    # ZAP returns exit codes based on findings:
    # 0 = no warnings/errors
    # 1 = warnings found
    # 2 = errors found
    # 3 = ZAP error
    
    case $exit_code in
        0)
            log_success "Baseline scan completed - No issues found"
            ;;
        1)
            log_warning "Baseline scan completed - Warnings found (see report)"
            ;;
        2)
            log_error "Baseline scan completed - Errors found (see report)"
            ;;
        *)
            log_error "Baseline scan failed with exit code: $exit_code"
            return $exit_code
            ;;
    esac
    
    return 0
}

# Run API scan
run_api_scan() {
    log_info "Starting OWASP ZAP API Scan..."
    log_info "Target: $TARGET_URL"
    log_info "Mode: OpenAPI import + Safe mode"
    
    # Prepare OpenAPI spec
    local openapi_spec
    openapi_spec=$(prepare_openapi_spec) || return 1
    
    local report_args
    report_args=$(generate_report_paths "api-scan")
    
    # Build ZAP command
    local zap_cmd="zap-api-scan.py"
    zap_cmd="$zap_cmd -t /zap/wrk/$(basename "$openapi_spec")"
    zap_cmd="$zap_cmd -f openapi"
    zap_cmd="$zap_cmd $report_args"
    
    if [ "$SAFE_MODE" = true ]; then
        zap_cmd="$zap_cmd -S"
    fi
    
    if [ -n "$CONFIG_FILE" ]; then
        zap_cmd="$zap_cmd -c /zap/wrk/$(basename "$CONFIG_FILE")"
    fi
    
    if [ "$VERBOSE" = true ]; then
        zap_cmd="$zap_cmd -d"
    fi
    
    log_verbose "ZAP command: $zap_cmd"
    
    # Run ZAP API scan
    local exit_code=0
    docker run --rm \
        -v "${OUTPUT_DIR}:/zap/wrk:rw" \
        ${CONFIG_FILE:+-v "${CONFIG_FILE}:/zap/wrk/$(basename "$CONFIG_FILE"):ro"} \
        "$ZAP_IMAGE" \
        $zap_cmd || exit_code=$?
    
    case $exit_code in
        0)
            log_success "API scan completed - No issues found"
            ;;
        1)
            log_warning "API scan completed - Warnings found (see report)"
            ;;
        2)
            log_error "API scan completed - Errors found (see report)"
            ;;
        *)
            log_error "API scan failed with exit code: $exit_code"
            return $exit_code
            ;;
    esac
    
    return 0
}

# Run full active scan
run_full_scan() {
    log_warning "Starting OWASP ZAP Full Active Scan..."
    log_warning "⚠️  WARNING: This scan sends ACTIVE ATTACKS and may MODIFY DATA"
    log_warning "⚠️  Only run against TEST ENVIRONMENTS with isolated databases"
    log_warning "Target: $TARGET_URL"
    
    # Safety check
    if [[ "$TARGET_URL" == *"localhost"* ]] || [[ "$TARGET_URL" == *"127.0.0.1"* ]]; then
        log_warning "Detected localhost target - proceeding with caution"
    elif [[ "$TARGET_URL" == *"prod"* ]] || [[ "$TARGET_URL" == *"production"* ]]; then
        log_error "PRODUCTION URL DETECTED! Refusing to run active scan."
        log_error "Active scans should NEVER be run against production."
        return 1
    fi
    
    # Prepare OpenAPI spec
    local openapi_spec
    openapi_spec=$(prepare_openapi_spec) || return 1
    
    local report_args
    report_args=$(generate_report_paths "full-scan")
    
    # Build ZAP command (no -S flag for active scanning)
    local zap_cmd="zap-api-scan.py"
    zap_cmd="$zap_cmd -t /zap/wrk/$(basename "$openapi_spec")"
    zap_cmd="$zap_cmd -f openapi"
    zap_cmd="$zap_cmd $report_args"
    
    if [ -n "$CONFIG_FILE" ]; then
        zap_cmd="$zap_cmd -c /zap/wrk/$(basename "$CONFIG_FILE")"
    fi
    
    if [ "$VERBOSE" = true ]; then
        zap_cmd="$zap_cmd -d"
    fi
    
    log_verbose "ZAP command: $zap_cmd"
    
    # Confirm before proceeding
    read -p "Are you sure you want to run ACTIVE SCAN? (yes/NO) " -r
    echo
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Full scan cancelled by user"
        return 0
    fi
    
    # Run ZAP full scan
    local exit_code=0
    docker run --rm \
        -v "${OUTPUT_DIR}:/zap/wrk:rw" \
        ${CONFIG_FILE:+-v "${CONFIG_FILE}:/zap/wrk/$(basename "$CONFIG_FILE"):ro"} \
        "$ZAP_IMAGE" \
        $zap_cmd || exit_code=$?
    
    case $exit_code in
        0)
            log_success "Full scan completed - No issues found"
            ;;
        1)
            log_warning "Full scan completed - Warnings found (see report)"
            ;;
        2)
            log_error "Full scan completed - Errors found (see report)"
            ;;
        *)
            log_error "Full scan failed with exit code: $exit_code"
            return $exit_code
            ;;
    esac
    
    return 0
}

# Run authenticated scan
run_authenticated_scan() {
    log_info "Starting OWASP ZAP Authenticated Scan..."
    
    if [ -z "$AUTH_TOKEN" ]; then
        log_error "Authentication token required for authenticated scan"
        log_error "Use --auth-token option to provide JWT token"
        return 1
    fi
    
    log_info "Target: $TARGET_URL"
    log_info "Mode: Authenticated with JWT token"
    
    # Prepare OpenAPI spec
    local openapi_spec
    openapi_spec=$(prepare_openapi_spec) || return 1
    
    local report_args
    report_args=$(generate_report_paths "authenticated-scan")
    
    # Create ZAP authentication config
    local auth_config="${RUN_DIR}/zap-auth-config.yaml"
    cat > "$auth_config" << EOF
env:
  contexts:
    - name: "API Authentication"
      urls:
        - "${TARGET_URL}/api/v1/.*"
      authentication:
        method: "scriptBased"
        parameters:
          script: "HTTPBearerToken.js"
          scriptEngine: "Oracle Nashorn"
        verification:
          method: "response"
          pollUrl: "${TARGET_URL}/health"
          pollData: ""
          pollFrequency: 60
          loggedInRegex: "\\\\Q200\\\\E"
          loggedOutRegex: "\\\\Q401\\\\E"
      authorization:
        method: "httpHeader"
        parameters:
          header: "Authorization"
          value: "Bearer ${AUTH_TOKEN}"
      users:
        - name: "authenticated-user"
          credentials:
            token: "${AUTH_TOKEN}"
EOF
    
    log_verbose "Created authentication config: $auth_config"
    
    # Build ZAP command with authentication
    local zap_cmd="zap-api-scan.py"
    zap_cmd="$zap_cmd -t /zap/wrk/$(basename "$openapi_spec")"
    zap_cmd="$zap_cmd -f openapi"
    zap_cmd="$zap_cmd $report_args"
    zap_cmd="$zap_cmd -n /zap/wrk/$(basename "$auth_config")"
    
    if [ "$SAFE_MODE" = true ]; then
        zap_cmd="$zap_cmd -S"
    fi
    
    if [ "$VERBOSE" = true ]; then
        zap_cmd="$zap_cmd -d"
    fi
    
    log_verbose "ZAP command: $zap_cmd"
    
    # Run ZAP authenticated scan
    local exit_code=0
    docker run --rm \
        -v "${OUTPUT_DIR}:/zap/wrk:rw" \
        "$ZAP_IMAGE" \
        $zap_cmd || exit_code=$?
    
    case $exit_code in
        0)
            log_success "Authenticated scan completed - No issues found"
            ;;
        1)
            log_warning "Authenticated scan completed - Warnings found (see report)"
            ;;
        2)
            log_error "Authenticated scan completed - Errors found (see report)"
            ;;
        *)
            log_error "Authenticated scan failed with exit code: $exit_code"
            return $exit_code
            ;;
    esac
    
    return 0
}

# Run all scans
run_all_scans() {
    log_info "Running all OWASP ZAP scan types..."
    
    local failed_scans=()
    
    # Baseline scan
    if ! run_baseline_scan; then
        failed_scans+=("baseline")
    fi
    
    # API scan
    if ! run_api_scan; then
        failed_scans+=("api")
    fi
    
    # Full scan (if not safe mode)
    if [ "$SAFE_MODE" = false ]; then
        log_warning "Skipping full active scan in 'all' mode for safety"
        log_info "Run 'full' scan type explicitly if needed"
    fi
    
    # Authenticated scan (if token provided)
    if [ -n "$AUTH_TOKEN" ]; then
        if ! run_authenticated_scan; then
            failed_scans+=("authenticated")
        fi
    else
        log_info "Skipping authenticated scan (no token provided)"
    fi
    
    # Report results
    echo
    log_info "==================================="
    log_info "All Scans Complete"
    log_info "==================================="
    
    if [ ${#failed_scans[@]} -eq 0 ]; then
        log_success "All scans completed successfully"
    else
        log_error "Some scans failed: ${failed_scans[*]}"
        return 1
    fi
    
    return 0
}

# Generate summary report
generate_summary() {
    log_info "Generating scan summary..."
    
    local summary_file="${RUN_DIR}/SCAN_SUMMARY.md"
    
    cat > "$summary_file" << EOF
# OWASP ZAP Scan Summary

**Date:** $(date '+%Y-%m-%d %H:%M:%S')  
**Scan Type:** ${SCAN_TYPE}  
**Target:** ${TARGET_URL}  
**Output Directory:** ${RUN_DIR}

## Configuration

- **Safe Mode:** ${SAFE_MODE}
- **Report Formats:** ${REPORT_FORMATS}
- **Authenticated:** $([ -n "$AUTH_TOKEN" ] && echo "Yes" || echo "No")
- **Config File:** $([ -n "$CONFIG_FILE" ] && echo "$(basename "$CONFIG_FILE")" || echo "None")

## Reports Generated

EOF
    
    # List all generated reports
    find "$RUN_DIR" -type f \( -name "*.html" -o -name "*.json" -o -name "*.md" -o -name "*.xml" \) | while read -r report; do
        echo "- \`$(basename "$report")\`" >> "$summary_file"
    done
    
    cat >> "$summary_file" << EOF

## Next Steps

1. **Review Reports:** Open HTML reports in browser
2. **Analyze Findings:** Check JSON reports for programmatic analysis
3. **Fix Issues:** Address critical and high severity findings
4. **Re-scan:** Verify fixes with follow-up scans

## References

- [OWASP ZAP Documentation](https://www.zaproxy.org/docs/)
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [API Security Top 10](https://owasp.org/API-Security/)

---
Generated by: \`$(basename "$0")\`
EOF
    
    log_success "Summary report generated: $summary_file"
    
    # Display summary
    cat "$summary_file"
}

# Main execution
main() {
    echo "========================================"
    echo "  OWASP ZAP Security Scanner"
    echo "========================================"
    echo
    
    # Check for help flag
    if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        show_help
    fi
    
    # Parse arguments
    parse_args "$@"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Setup output directory
    setup_output_dir
    
    # Change to repo root for relative paths
    cd "$REPO_ROOT"
    
    # Execute scan based on type
    case "$SCAN_TYPE" in
        baseline)
            run_baseline_scan
            ;;
        api)
            run_api_scan
            ;;
        full)
            run_full_scan
            ;;
        authenticated)
            run_authenticated_scan
            ;;
        all)
            run_all_scans
            ;;
        *)
            log_error "Unknown scan type: $SCAN_TYPE"
            echo "Valid scan types: baseline, api, full, authenticated, all"
            echo "Run '$(basename "$0") --help' for more information"
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_summary
    
    log_success "OWASP ZAP scan complete!"
    log_info "Results saved to: $RUN_DIR"
}

# Run main function
main "$@"
