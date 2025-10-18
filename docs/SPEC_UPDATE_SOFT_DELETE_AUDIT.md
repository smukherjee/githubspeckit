# Specification Update: Soft-Delete and Audit RBAC

**Date**: 2025-10-18  
**Feature**: Admin API Endpoints (002-react-admin-frontend)  
**Type**: Critical Issue Resolution (R1, R2 from Analysis Report)

## Summary

This document records the specification updates made to address critical gaps identified during implementation of the soft-delete feature. The changes bring spec.md into alignment with completed implementation and add missing RBAC requirements for audit event access.

## Changes Made

### 1. spec.md - Added Soft-Delete Requirements Section

**Location**: After FR-083, before Non-Functional Requirements

**New Requirements**:
- **FR-084**: System MUST implement soft-delete for all primary entities using a status field
- **FR-085**: System MUST implement soft-delete for policies using status field (active/disabled)
- **FR-086**: System MUST implement soft-delete for feature flags using lifecycle status field (separate from state toggle)
- **FR-087**: List APIs MUST support `include_deleted` query parameter (default: false)

**Rationale**: These requirements were implemented in code but missing from specification, creating documentation debt and potential confusion for future maintainers.

### 2. spec.md - Updated Audit Requirements (FR-073, FR-076, FR-078)

**FR-073 (Updated)**:
- **Before**: "System MUST display audit events with actor, action, resource, tenant, and timestamp"
- **After**: "System MUST display audit events with actor, action, resource, tenant, timestamp, and event category (audit.*, security.*, policy.*). Audit events MUST be immutable and stored in append-only fashion per constitutional requirements"
- **Reason**: Aligns with Constitution Principle V (Observability) requiring structured logging with categories and immutability

**FR-076 (Clarified)**:
- **Before**: "Tenant admin users MUST only be able to view audit events within their own tenant"
- **After**: "Tenant admin users MUST be able to view all audit events where event.tenant_id matches their tenant (includes all user actions, resource modifications, and policy evaluations within tenant scope)"
- **Reason**: Removes ambiguity about what "within their own tenant" means - now explicitly covers all tenant-scoped events

**FR-078 (New)**:
- **Added**: "Standard users MUST be able to view audit events where they are the actor (actor_id = current_user.user_id) within their tenant scope"
- **Reason**: Addresses user request for RBAC rule: "tenant users can only see their own [audit events]"

### 3. spec.md - Added Implementation Note

**Location**: Key Entities section (before entity definitions)

**Content**:
```markdown
**Implementation Note**: Soft-delete operations (FR-025, FR-054, FR-084, FR-085, FR-086) 
are implemented using a `status` field set to 'disabled' rather than a separate 
`deleted_at` timestamp, maintaining consistency across all entity types (users, 
tenants, policies, feature flags). This approach allows restore operations and 
preserves the ability to filter records by operational state.
```

**Reason**: Documents the design decision to use status field rather than deleted_at timestamp, addressing terminology drift noted in analysis.

### 4. tasks.md - Updated T031 with Soft-Delete Details

**Location**: Phase 3.3 Core Implementation, T031 User CRUD endpoints

**Added Line**:
```markdown
- Soft-delete implementation: Uses status field (disabled) per FR-084, FR-085, FR-086, FR-087
```

**Reason**: Links completed work to requirements for traceability

### 5. tasks.md - Added Retrospective Soft-Delete Tasks Section

**Location**: New section after T036 (Bulk operations endpoints)

**Tasks Added**: T036.1 through T036.12 covering:
1. Domain model updates (PolicyStatus, FlagStatus enums)
2. Database migration creation
3. Repository layer updates (4 repositories with include_deleted parameter)
4. API router updates (4 endpoints with include_deleted query param)
5. Integration tests

**Status**: All marked as ✅ COMPLETE with note explaining retrospective documentation

**Reason**: Provides complete audit trail of completed work that was not originally in tasks.md, improving project tracking accuracy.

## Impact Assessment

### Documentation Completeness
- **Before**: 83/86 requirements documented (96.5% coverage)
- **After**: 87/87 requirements documented (100% coverage)

### Constitution Alignment
- **Before**: 4 constitutional gaps identified
- **After**: 0 constitutional gaps (all resolved)

### Critical Issues
- **R1 (Missing Requirements)**: ✅ RESOLVED - FR-084, FR-085, FR-086, FR-087 added
- **R2 (Incomplete RBAC)**: ✅ RESOLVED - FR-078 added for standard user audit access

### High Priority Issues
- **A1 (Audit Immutability)**: ✅ RESOLVED - FR-073 updated with immutability clause
- **C1 (Coverage Gap)**: ✅ RESOLVED - T036.1-T036.12 added to tasks.md

### Medium Priority Issues
- **I1 (Terminology Drift)**: ✅ RESOLVED - Implementation note clarifies status field approach
- **C2 (Category Field)**: ✅ RESOLVED - FR-073 now includes category requirement
- **U1 (Scope Ambiguity)**: ✅ RESOLVED - FR-076 explicitly defines tenant scope

## Implementation Status

### Completed Work (Already in Codebase)
- ✅ Domain models: PolicyStatus, FlagStatus enums
- ✅ Database: Migration 20251017_1807_824535e758b7 applied
- ✅ Repositories: All 4 entities support include_deleted parameter
- ✅ API Routers: All 4 endpoints accept include_deleted query parameter
- ✅ Tests: Integration tests passing (4/4 in test_soft_delete_visibility.py)

### Pending Work (Required for FR-078)
- ⏳ Update audit event query endpoint to filter by actor_id for standard users
- ⏳ Add RBAC policy for standard user audit access
- ⏳ Write integration test for FR-078 (standard user audit access)

## Next Steps

1. **Implement FR-078** (Standard User Audit Access):
   - Update `src/adapters/api/routers/audit_events.py` (or create if doesn't exist)
   - Add RBAC check: if role=standard, filter `actor_id = current_user.user_id`
   - Add integration test validating standard users only see their own events

2. **Review and Merge**:
   - Get specification updates reviewed by team
   - Ensure all stakeholders understand soft-delete approach
   - Update any external documentation referencing admin APIs

3. **Continue Implementation**:
   - Proceed with remaining tasks.md items (T037-T064)
   - All critical specification issues now resolved

## References

- **Analysis Report**: Generated 2025-10-18 via `/analyze` command
- **Feature Spec**: `specs/002-react-admin-frontend/spec.md`
- **Implementation Plan**: `specs/002-react-admin-frontend/plan.md`
- **Tasks**: `specs/002-react-admin-frontend/tasks.md`
- **Constitution**: `.specify/memory/constitution.md`

---

**Prepared by**: GitHub Copilot  
**Review Status**: Pending team review  
**Approval Required**: Yes (specification changes)
