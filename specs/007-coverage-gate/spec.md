# Feature Specification: CI Coverage Gate Enforcement

**Feature ID**: 007  
**Priority**: 🔴 BLOCKING (MUST DO BEFORE /implement)  
**Status**: Planning  
**Owner**: DevOps Team  
**Timeline**: 4 hours  
**Related Findings**: CON1 (CRITICAL)

## Overview

Implement automated CI coverage gate enforcing Constitution Principle II thresholds: ≥90% domain layer, ≥85% overall, 100% critical auth/tenancy paths. Blocks merge if coverage drops below thresholds.

## Problem Statement

**Constitutional Requirement**: Principle II mandates "≥90% domain, ≥85% overall; 100% critical auth/tenancy paths"

**Current State**:

- ✅ Coverage measured locally via pytest-cov
- ❌ No CI gate blocking merge if coverage drops
- ❌ No coverage_critical_paths.yml manifest
- ❌ No automated reporting to pull requests

**Constitutional Violation**: CON1 - Cannot guarantee coverage thresholds maintained over time.

## Functional Requirements

### FR-106: Coverage Gate Script

**Priority**: P0 (CRITICAL)

**Acceptance Criteria**:

- ✅ Script: `scripts/coverage_gate.py`
- ✅ Parse coverage XML (`coverage.xml`)
- ✅ Enforce thresholds: domain ≥90%, overall ≥85%
- ✅ Check critical paths manifest: 100% statement coverage
- ✅ Output: Structured JSON summary
- ✅ Exit code 1 if thresholds violated

### FR-107: Critical Paths Manifest

**Priority**: P0 (CRITICAL)

**Acceptance Criteria**:

- ✅ File: `coverage_critical_paths.yml`
- ✅ Lists files requiring 100% coverage:

```yaml
critical_paths:
  - src/auth_core/token_validation.py
  - src/domain/tenants/tenant_context.py
  - src/adapters/api/middleware/auth.py
  - src/adapters/api/middleware/tenant_isolation.py
```

- ✅ Manifest edits require security reviewer approval

### FR-108: GitHub Actions Integration

**Priority**: P0 (CRITICAL)

**Acceptance Criteria**:

- ✅ CI workflow step: `make coverage-gate`
- ✅ Runs after test suite completes
- ✅ Fails pipeline if coverage gate fails
- ✅ Posts comment to PR with coverage summary
- ✅ Generates coverage badge for README

### FR-109: Coverage Regression Detection

**Priority**: P1 (HIGH)

**Acceptance Criteria**:

- ✅ Compare current coverage to main branch
- ✅ Warn if overall coverage drops >0.5%
- ✅ Block if overall coverage drops >1.0%
- ✅ Allow drop if justification comment present: `JUSTIFY: COVER-001`

## Success Criteria

**Exit Criteria**:

- ✅ CON1 finding resolved
- ✅ CI fails if coverage <85% overall or <90% domain
- ✅ Critical paths enforced at 100%
- ✅ Coverage badge in README
- ✅ Documentation: CONTRIBUTING.md updated

**Metrics**:

- **Enforcement**: 100% of PRs pass coverage gate before merge
- **Coverage Trend**: No degradation >0.5% per quarter
- **Critical Paths**: 100% coverage maintained continuously

## Technical Implementation

```python
# scripts/coverage_gate.py
import xml.etree.ElementTree as ET
import yaml
import sys

def parse_coverage_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    
    # Parse overall coverage
    overall = float(root.attrib['line-rate']) * 100
    
    # Parse domain coverage
    domain_packages = [pkg for pkg in root.findall('.//package') 
                      if 'src/domain' in pkg.attrib['name']]
    domain_coverage = calculate_coverage(domain_packages)
    
    return {
        'overall': overall,
        'domain': domain_coverage,
        'files': parse_file_coverage(root)
    }

def enforce_thresholds(coverage, critical_paths):
    failures = []
    
    if coverage['overall'] < 85.0:
        failures.append(f"Overall coverage {coverage['overall']:.1f}% < 85%")
    
    if coverage['domain'] < 90.0:
        failures.append(f"Domain coverage {coverage['domain']:.1f}% < 90%")
    
    for path in critical_paths:
        file_cov = coverage['files'].get(path, 0)
        if file_cov < 100.0:
            failures.append(f"Critical path {path}: {file_cov:.1f}% < 100%")
    
    return failures

if __name__ == '__main__':
    coverage = parse_coverage_xml('coverage.xml')
    critical_paths = yaml.safe_load(open('coverage_critical_paths.yml'))['critical_paths']
    
    failures = enforce_thresholds(coverage, critical_paths)
    
    if failures:
        print("❌ Coverage gate FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ Coverage gate PASSED: overall={coverage['overall']:.1f}%, domain={coverage['domain']:.1f}%")
        sys.exit(0)
```

## GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-report=html
      
      - name: Coverage gate
        run: |
          python scripts/coverage_gate.py
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
      
      - name: Comment PR with coverage
        if: github.event_name == 'pull_request'
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ github.token }}
```

## Appendix

**Related Documents**:

- Constitution Principle II: Coverage Requirements
- Security Analysis Report: Finding CON1
- CONTRIBUTING.md: Coverage enforcement guidelines
