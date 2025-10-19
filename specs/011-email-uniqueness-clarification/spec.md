# Feature Specification: Email Uniqueness Clarification

**Feature ID**: 011  
**Priority**: 🟢 MEDIUM (Before v2.0)  
**Status**: Planning  
**Owner**: Product Team  
**Timeline**: 1 day  
**Related Findings**: U1 (MEDIUM)

## Overview

Document email uniqueness strategy: Global (across all tenants) vs per-tenant. Update FR-019 in spec.md.

## Functional Requirements

### FR-113: Email Uniqueness Strategy Documentation

**Acceptance Criteria**:

- ✅ Decision: Global uniqueness (recommended) or per-tenant
- ✅ Rationale documented in FR-019
- ✅ Database constraints updated (UNIQUE vs UNIQUE(email, tenant_id))
- ✅ Tests cover uniqueness violations
- ✅ Error messages clarified

## Success Criteria

- ✅ U1 finding resolved
- ✅ FR-019 updated
- ✅ Database migration created (if needed)
- ✅ Tests passing
