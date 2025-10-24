# OWASP ZAP Security Scanning Guide

This guide provides comprehensive documentation for running OWASP ZAP security scans against the githubspeckit application using the automated scanning script.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Scan Types](#scan-types)
- [Usage Examples](#usage-examples)
- [Configuration Options](#configuration-options)
- [Report Interpretation](#report-interpretation)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

### What is OWASP ZAP?

OWASP ZAP (Zed Attack Proxy) is an open-source web application security scanner maintained by the OWASP Foundation. It helps identify security vulnerabilities in web applications through:

- **Passive Scanning**: Monitors traffic without modifying requests
- **Active Scanning**: Sends malicious payloads to test for vulnerabilities
- **Spider**: Crawls the application to discover endpoints
- **API Scanning**: Tests API endpoints using OpenAPI specifications

### Security Testing Coverage

Our ZAP configuration tests for:

- **OWASP Top 10 2021**: All critical web application security risks
- **SQL Injection**: Database attack vectors
- **Cross-Site Scripting (XSS)**: JavaScript injection vulnerabilities
- **Command Injection**: OS command execution vulnerabilities
- **Path Traversal**: Unauthorized file access attempts
- **XML External Entity (XXE)**: XML parser vulnerabilities
- **Server-Side Request Forgery (SSRF)**: Internal resource access
- **Security Headers**: HTTP header best practices
- **Authentication/Authorization**: RBAC and access control testing

### Tool Location

The scanning script is located at:
```
scripts/security/run-zap-scan.sh
```

---

## Quick Start

### Prerequisites

1. **Docker**: ZAP runs in a Docker container
   ```bash
   docker --version  # Verify Docker is installed
   ```

2. **Running Application**: The target application must be accessible
   ```bash
   # Start the application (in separate terminal)
   source .venv/bin/activate && python -m src.adapters.api.app
   
   # Or use Makefile
   make api
   ```

3. **Permissions**: Ensure the script is executable
   ```bash
   chmod +x scripts/security/run-zap-scan.sh
   ```

### Running Your First Scan

**Option 1: Using the Script Directly**
```bash
# Run a quick baseline scan
./scripts/security/run-zap-scan.sh baseline
```

**Option 2: Using Makefile**
```bash
# Run a baseline scan
make security-baseline
```

The scan will:
1. Pull the OWASP ZAP Docker image (first time only)
2. Scan your application at `http://localhost:8000`
3. Generate reports in `reports/security/zap/run_YYYYMMDD_HHMMSS/`
4. Display a summary with findings

---

## Scan Types

### 1. Baseline Scan (Passive)

**Purpose**: Quick security check safe for production environments

**What it does**:
- Passive traffic monitoring only
- No modification of requests
- Detects common security issues
- Safe to run against live systems

**When to use**:
- Pre-deployment validation
- Production environment checks
- Quick security health checks
- CI/CD pipelines

**Command**:
```bash
# Script
./scripts/security/run-zap-scan.sh baseline

# Makefile
make security-baseline
```

**Typical duration**: 30-60 seconds

---

### 2. API Scan

**Purpose**: Comprehensive API security testing using OpenAPI specification

**What it does**:
- Imports OpenAPI spec from `/openapi.json`
- Tests all documented API endpoints
- Validates request/response formats
- Checks authentication mechanisms
- Tests input validation

**When to use**:
- After API changes
- API-focused security testing
- OpenAPI contract validation
- REST API security audits

**Command**:
```bash
# Script
./scripts/security/run-zap-scan.sh api

# Makefile
make security-api
```

**Typical duration**: 2-3 minutes

**Requirements**: Application must expose `/openapi.json` endpoint

---

### 3. Full Scan (Active)

**Purpose**: Deep security testing with active attack vectors

**What it does**:
- Sends malicious payloads
- Tests SQL injection, XSS, command injection
- Path traversal attempts
- XXE and SSRF testing
- **MODIFIES DATA** - Use test environments only!

**When to use**:
- Pre-release security audits
- Test environments only
- Isolated test databases
- Comprehensive vulnerability discovery

**Command**:
```bash
# Script (with safety confirmation)
./scripts/security/run-zap-scan.sh full

# Makefile (safe mode enabled)
make security-full

# Script with explicit target
./scripts/security/run-zap-scan.sh full --target http://test.local:8000
```

**Typical duration**: 10-20 minutes

**⚠️ WARNING**: 
- Never run against production!
- Requires isolated test database
- May trigger security monitoring alerts
- Can cause data corruption

---

### 4. Authenticated Scan

**Purpose**: Test authorization and RBAC with valid credentials

**What it does**:
- Scans with JWT authentication
- Tests role-based access control
- Validates tenant isolation
- Checks authorization bypass vulnerabilities

**When to use**:
- RBAC implementation validation
- Multi-tenant isolation testing
- Authorization flow verification
- Privilege escalation testing

**Command**:
```bash
# First, obtain a JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"SecurePass123!"}' | \
  jq -r '.access_token')

# Script
./scripts/security/run-zap-scan.sh authenticated --auth-token "$TOKEN"

# Makefile
AUTH_TOKEN="$TOKEN" make security-authenticated
```

**Typical duration**: 5-10 minutes

**Requirements**: Valid JWT token for authentication

---

### 5. All Scans

**Purpose**: Comprehensive security audit with all scan types

**What it does**:
- Runs baseline → api → full → authenticated sequentially
- Generates separate reports for each scan type
- Creates consolidated summary

**When to use**:
- Quarterly security audits
- Pre-release comprehensive testing
- Security compliance validation
- Major version releases

**Command**:
```bash
# Script
./scripts/security/run-zap-scan.sh all --verbose

# Makefile
make security-all
```

**Typical duration**: 20-30 minutes

---

## Usage Examples

### Example 1: Quick Production Check

```bash
# Run baseline scan against production
./scripts/security/run-zap-scan.sh baseline \
  --target https://api.production.example.com \
  --output /tmp/prod-scan
```

### Example 2: Detailed API Testing

```bash
# API scan with all report formats
./scripts/security/run-zap-scan.sh api \
  --target http://localhost:8000 \
  --format html,json,md,xml \
  --verbose
```

### Example 3: Test Environment Full Scan

```bash
# Full active scan in test environment
./scripts/security/run-zap-scan.sh full \
  --target http://test.local:8000 \
  --output reports/security/full-test-$(date +%Y%m%d)
```

### Example 4: Authenticated RBAC Testing

```bash
# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"SecurePass123!"}' | \
  jq -r '.access_token')

# Run authenticated scan
./scripts/security/run-zap-scan.sh authenticated \
  --auth-token "$ADMIN_TOKEN" \
  --verbose
```

### Example 5: Custom ZAP Configuration

```bash
# Create custom ZAP rules
cat > /tmp/zap-rules.conf <<EOF
# Aggressive scan policy
scanner.strength=INSANE
scanner.alertthreshold=LOW
EOF

# Run with custom config
./scripts/security/run-zap-scan.sh api \
  --config /tmp/zap-rules.conf \
  --verbose
```

---

## Configuration Options

### Command-Line Arguments

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--target` | `-t` | Target URL to scan | `http://localhost:8000` |
| `--output` | `-o` | Output directory for reports | `reports/security/zap` |
| `--format` | `-f` | Report formats (comma-separated) | `html,json,md` |
| `--config` | `-c` | ZAP configuration file | None |
| `--auth-token` | `-a` | JWT token for authenticated scans | None |
| `--safe` | `-s` | Safe mode (disable active attacks) | `false` |
| `--verbose` | `-v` | Verbose debug output | `false` |
| `--help` | `-h` | Show help message | - |

### Report Formats

- **HTML**: Human-readable browsable report with findings
- **JSON**: Machine-parsable for automation/CI integration
- **Markdown**: Developer-friendly documentation format
- **XML**: Compatible with SAST tools and dashboards

### Environment Variables

```bash
# Override Docker image
export ZAP_IMAGE="ghcr.io/zaproxy/zaproxy:weekly"

# Change default target
export TARGET_URL="http://staging.example.com"

# Set authentication token
export AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Report Interpretation

### Report Structure

Each scan generates a timestamped directory:
```
reports/security/zap/
└── run_20250123_143022/
    ├── baseline-report.html      # Browsable HTML report
    ├── baseline-report.json      # Machine-readable JSON
    ├── baseline-report.md        # Markdown summary
    ├── baseline-report.xml       # XML for SAST tools
    └── SCAN_SUMMARY.md           # Executive summary
```

### Severity Levels

| Level | Risk | Action Required |
|-------|------|-----------------|
| **Critical** | Immediate exploitation possible | Fix within 24 hours |
| **High** | High impact vulnerability | Fix within 7 days |
| **Medium** | Moderate security risk | Fix within 30 days |
| **Low** | Defense-in-depth improvement | Fix when convenient |
| **Informational** | Best practice recommendation | Review and consider |

### Common Findings

#### 1. Missing Security Headers

**Finding**: `X-Content-Type-Options` header not set

**Severity**: Low

**Remediation**:
```python
# src/adapters/api/security_headers.py
response.headers["X-Content-Type-Options"] = "nosniff"
```

#### 2. SQL Injection

**Finding**: SQL injection vulnerability detected

**Severity**: Critical

**Remediation**:
```python
# Use parameterized queries
await db.execute(
    "SELECT * FROM users WHERE id = :id",
    {"id": user_id}  # ✅ Safe
)

# NEVER use string concatenation
# await db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # ❌ Vulnerable
```

#### 3. XSS (Cross-Site Scripting)

**Finding**: Reflected XSS in error messages

**Severity**: High

**Remediation**:
```python
# Sanitize user input
from markupsafe import escape

error_msg = f"Invalid input: {escape(user_input)}"
```

#### 4. Authentication Bypass

**Finding**: Endpoint accessible without authentication

**Severity**: Critical

**Remediation**:
```python
# Add authentication dependency
@router.get("/admin/users")
async def list_users(
    current_user: User = Depends(get_current_active_user)
):
    ...
```

### Exit Codes

The script returns standard exit codes for CI/CD integration:

- `0`: Success - No vulnerabilities found
- `1`: Warnings - Low severity findings
- `2`: Errors - Medium/High/Critical findings
- `3`: ZAP execution failure

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/security-scan.yml`:

```yaml
name: Security Scan

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install -r requirements.txt
      
      - name: Start application
        run: |
          source .venv/bin/activate
          python -m src.adapters.api.app &
          sleep 10
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost/test_db
      
      - name: Run baseline scan
        run: |
          ./scripts/security/run-zap-scan.sh baseline \
            --target http://localhost:8000 \
            --output /tmp/zap-reports
      
      - name: Upload scan results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: zap-scan-reports
          path: /tmp/zap-reports/
      
      - name: Check for vulnerabilities
        run: |
          # Fail build if medium+ severity findings
          jq -e '.site[0].alerts[] | select(.risk == "Medium" or .risk == "High" or .risk == "Critical")' \
            /tmp/zap-reports/run_*/baseline-report.json && exit 1 || exit 0
```

### GitLab CI Example

Add to `.gitlab-ci.yml`:

```yaml
security_scan:
  stage: test
  image: python:3.13
  
  services:
    - postgres:16
  
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_pass
  
  before_script:
    - apt-get update && apt-get install -y docker.io
    - python -m venv .venv
    - source .venv/bin/activate
    - pip install -r requirements.txt
  
  script:
    # Start application
    - python -m src.adapters.api.app &
    - sleep 10
    
    # Run ZAP scan
    - ./scripts/security/run-zap-scan.sh baseline
  
  artifacts:
    when: always
    paths:
      - reports/security/zap/
    expire_in: 30 days
  
  only:
    - merge_requests
    - main
```

### Jenkins Pipeline Example

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    stages {
        stage('Security Scan') {
            steps {
                script {
                    // Start application
                    sh '''
                        source .venv/bin/activate
                        python -m src.adapters.api.app &
                        sleep 10
                    '''
                    
                    // Run ZAP scan
                    sh './scripts/security/run-zap-scan.sh baseline'
                    
                    // Archive reports
                    archiveArtifacts artifacts: 'reports/security/zap/**/*', fingerprint: true
                    
                    // Publish HTML report
                    publishHTML([
                        reportDir: 'reports/security/zap',
                        reportFiles: '*/baseline-report.html',
                        reportName: 'OWASP ZAP Report'
                    ])
                }
            }
        }
    }
    
    post {
        always {
            // Clean up
            sh 'pkill -f "python -m src.adapters.api.app" || true'
        }
    }
}
```

---

## Troubleshooting

### Issue 1: Docker Not Running

**Error**:
```
ERROR: Cannot connect to Docker daemon
```

**Solution**:
```bash
# Check Docker status
docker info

# Start Docker (macOS)
open -a Docker

# Start Docker (Linux)
sudo systemctl start docker
```

---

### Issue 2: Target Application Not Accessible

**Error**:
```
ERROR: Target http://localhost:8000 is not responding
Health check failed: curl: (7) Failed to connect
```

**Solution**:
```bash
# Check if application is running
curl http://localhost:8000/health

# Start application if needed
source .venv/bin/activate && python -m src.adapters.api.app

# Or use Makefile
make api
```

---

### Issue 3: Permission Denied

**Error**:
```
bash: ./scripts/security/run-zap-scan.sh: Permission denied
```

**Solution**:
```bash
# Make script executable
chmod +x scripts/security/run-zap-scan.sh
```

---

### Issue 4: OpenAPI Spec Not Found

**Error**:
```
ERROR: Failed to download OpenAPI spec from http://localhost:8000/openapi.json
```

**Solution**:
```bash
# Verify OpenAPI endpoint
curl http://localhost:8000/openapi.json

# If missing, ensure FastAPI app has OpenAPI enabled
# In src/adapters/api/app.py:
app = FastAPI(
    title="GitHubSpecKit API",
    openapi_url="/openapi.json"  # Ensure this is set
)
```

---

### Issue 5: ZAP Scan Timeout

**Error**:
```
ERROR: ZAP scan exceeded maximum duration (30 minutes)
```

**Solution**:
```bash
# Reduce scan scope
./scripts/security/run-zap-scan.sh baseline --safe

# Or increase timeout in script
# Edit scripts/security/run-zap-scan.sh
# SCAN_TIMEOUT=3600  # 60 minutes
```

---

### Issue 6: High Memory Usage

**Error**:
```
ZAP container killed (OOM - Out of Memory)
```

**Solution**:
```bash
# Limit Docker memory
docker run --memory="2g" --memory-swap="2g" ...

# Or edit script to add memory limits
# In run-zap-scan.sh, add to docker run:
--memory="2g" --memory-swap="2g"
```

---

### Issue 7: False Positive Findings

**Finding**: ZAP reports vulnerabilities that don't actually exist

**Solution**:
```bash
# Create custom ZAP rules to suppress false positives
cat > config/zap/custom-rules.conf <<EOF
# Suppress specific alert IDs
# 10021 = X-Content-Type-Options Header Missing (if intentional)
-config alert.10021.enabled=false

# Adjust risk threshold
-config scanner.alertthreshold=MEDIUM
EOF

# Run with custom config
./scripts/security/run-zap-scan.sh api --config config/zap/custom-rules.conf
```

---

## Best Practices

### 1. Regular Scanning Schedule

```bash
# Daily baseline scans (CI/CD)
- Automated on every PR
- Quick feedback loop
- Safe for all environments

# Weekly API scans
- Comprehensive endpoint coverage
- OpenAPI contract validation
- Test environment recommended

# Monthly full scans
- Active attack vectors
- Isolated test environment
- Fresh test database

# Quarterly authenticated scans
- RBAC validation
- Multi-tenant isolation
- Privilege escalation testing
```

### 2. Environment Separation

```bash
# ✅ Development
./scripts/security/run-zap-scan.sh baseline --target http://localhost:8000

# ✅ Staging
./scripts/security/run-zap-scan.sh api --target https://staging.example.com

# ✅ Test (full scans)
./scripts/security/run-zap-scan.sh full --target http://test.local:8000

# ❌ Production (NEVER run active scans)
# ./scripts/security/run-zap-scan.sh full --target https://production.example.com  # NEVER!
```

### 3. Report Management

```bash
# Archive reports by date
mkdir -p reports/security/zap/archive/$(date +%Y/%m)
mv reports/security/zap/run_* reports/security/zap/archive/$(date +%Y/%m)/

# Track findings in issue tracker
# Parse JSON and create GitHub issues for medium+ severity
jq -r '.site[0].alerts[] | select(.risk == "Medium" or .risk == "High" or .risk == "Critical") | 
  "[\(.risk)] \(.alert) - \(.desc)"' \
  reports/security/zap/run_*/api-scan-report.json | \
  while read issue; do
    gh issue create --title "Security: $issue" --label security,vulnerability
  done
```

### 4. Continuous Monitoring

```bash
# Set up GitHub Actions for automated scanning
# Track security metrics over time
# Alert on new vulnerabilities
# Integrate with Slack/Teams/Email notifications
```

### 5. Defense in Depth

```bash
# Combine ZAP with other tools:
- Static Application Security Testing (SAST): Bandit, Semgrep
- Dependency scanning: Safety, pip-audit
- Secret scanning: Gitleaks, TruffleHog
- Container scanning: Trivy, Grype
```

### 6. Remediation Workflow

```
1. Scan → Identify vulnerabilities
2. Prioritize → Critical/High first
3. Fix → Apply remediation
4. Verify → Re-scan to confirm fix
5. Document → Update security documentation
6. Monitor → Track for regressions
```

---

## Additional Resources

### OWASP Documentation

- [OWASP ZAP User Guide](https://www.zaproxy.org/docs/)
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)

### Internal Documentation

- [OWASP ZAP Findings Report](./OWASP_ZAP_FINDINGS.md)
- [OWASP ZAP Implementation Complete](./OWASP_ZAP_IMPLEMENTATION_COMPLETE.md)
- [Security Headers Implementation](../src/adapters/api/security_headers.py)

### Makefile Targets

```bash
make security-baseline       # Quick baseline scan
make security-api            # API scan with OpenAPI
make security-full           # Full active scan (test only!)
make security-authenticated  # Authenticated RBAC testing
make security-all            # All scans sequentially
make security-scan           # Alias for baseline
```

---

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [OWASP ZAP documentation](https://www.zaproxy.org/docs/)
3. Open a GitHub issue with:
   - Command executed
   - Error message
   - Target environment details
   - ZAP version (`docker run --rm ghcr.io/zaproxy/zaproxy:stable -version`)

---

**Last Updated**: 2025-01-23  
**Script Version**: 1.0.0  
**ZAP Version**: 2.16.1 (stable)
