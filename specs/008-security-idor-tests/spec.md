# Feature Specification: OWASP A01 IDOR Security Testing

**Feature ID**: 008  
**Priority**: 🟡 HIGH (Before Production Launch)  
**Status**: Planning  
**Owner**: Security Team  
**Timeline**: 3 days  
**Related Findings**: S3 (HIGH)

## Overview

Add comprehensive contract tests for OWASP A01:2021 (Broken Access Control) / IDOR (Insecure Direct Object Reference) vulnerabilities. Ensures 100% OWASP Top 10 coverage.

## Functional Requirements

### FR-110: IDOR Attack Contract Tests

**Acceptance Criteria**:

- ✅ Test: Standard user attempts cross-tenant resource access (expect 403)
- ✅ Test: User modifies `tenant_id` in path parameter (expect 403 if not superadmin)
- ✅ Test: User attempts to access another user's profile (expect 403)
- ✅ Test: Superadmin cross-tenant access succeeds with audit log
- ✅ Test: Session hijacking attempt (invalid session token)
- ✅ Test: Privilege escalation (standard user assigns superadmin role)
- ✅ All tests under `tests/contract/security/test_idor.py`

## Success Criteria

- ✅ S3 finding resolved
- ✅ 20+ IDOR contract tests covering all attack vectors
- ✅ 100% pass rate
- ✅ OWASP ZAP authenticated scan confirms IDOR protections
