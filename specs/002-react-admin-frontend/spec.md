# Feature Specification: React-Admin Frontend for Multi-Tenant Backend

**Feature Branch**: `002-react-admin-frontend`  
**Created**: 2025-10-05  
**Status**: Specification Complete  
**Input**: User description: "Create admin screens - should be created as a separate entity"

## Overview

This feature provides a web-based administrative interface for managing the multi-tenant backend system. The interface enables different user roles (superadmin, tenant_admin, standard) to perform operations within their authorized scope across tenants, users, feature flags, policies, invitations, and audit logs.

## User Scenarios & Testing

### Primary User Stories

**Story 1: Superadmin Cross-Tenant Management**

As a superadmin, I need to manage multiple tenant organizations from a single interface so that I can oversee the entire system without switching between separate logins.

**Story 2: Tenant Admin User Management**

As a tenant administrator, I need to create and manage users within my organization so that I can control who has access to our tenant's data and features.

**Story 3: Standard User Self-Service**

As a standard user, I need to view my profile and access permitted resources within my tenant so that I can perform my assigned responsibilities.

### Acceptance Scenarios

#### Scenario 1: Superadmin Tenant Switching

1. **Given** a superadmin is logged into the admin interface
2. **When** they select a different tenant from the tenant dropdown in the header
3. **Then** all subsequent operations send requests with the selected tenant_id parameter
4. **And** the interface displays data scoped to the selected tenant

#### Scenario 2: Tenant Admin User Creation

1. **Given** a tenant admin is logged into the admin interface
2. **When** they navigate to the Users screen and click "Create User"
3. **Then** they see a form with fields for email, roles, and status
4. **And** the tenant_id is automatically set to their own tenant (read-only)
5. **When** they submit the form with valid data
6. **Then** the new user is created in their tenant
7. **And** they see a success notification

#### Scenario 3: Standard User Profile Access

1. **Given** a standard user is logged into the admin interface
2. **When** they navigate to their profile via the user menu
3. **Then** they see their email, roles, tenant name, and account status
4. **And** all administrative screens (Users, Tenants, Policies) are hidden from navigation

#### Scenario 4: Authentication Token Refresh

1. **Given** a user is logged into the admin interface
2. **When** their short-lived access token expires (e.g., after 15 minutes)
3. **Then** the system automatically exchanges the HttpOnly refresh token for a new access token
4. **And** the user's session continues without interruption or re-login

#### Scenario 5: Role-Based Screen Visibility

1. **Given** a standard user has "readonly" permission for Feature Flags
2. **When** they navigate to the Feature Flags screen
3. **Then** they see the list of feature flags with view details capability
4. **And** the "Create", "Edit", and "Delete" buttons are hidden

#### Scenario 6: Unauthorized Access Prevention

1. **Given** a tenant admin is logged into the admin interface
2. **When** they attempt to create a new tenant (superadmin-only operation)
3. **Then** the interface returns a 403 Forbidden error
4. **And** displays a user-friendly message: "Only superadmins can create tenants"

### Edge Cases

- **Token expiration during form submission**: System should retry the request with refreshed token before showing an error
- **Tenant switching with unsaved form data**: Interface should warn user before switching contexts and losing draft data
- **Backend role change during active session**: User should be prompted to re-authenticate when token refresh detects role modification
- **Network interruption during API call**: Interface should show loading state and retry with exponential backoff
- **Invalid tenant_id in superadmin dropdown**: System should validate tenant exists before allowing selection
- **User disabled while logged in**: Next API call should detect 401/403 and redirect to login screen

## Requirements

### Functional Requirements

#### Authentication & Authorization

- **FR-001**: System MUST authenticate users via email and password credentials
- **FR-002**: System MUST issue short-lived access tokens (e.g., 15 minutes) stored in client-side storage
- **FR-003**: System MUST issue long-lived refresh tokens (e.g., 7 days) stored as HttpOnly, Secure, SameSite=None cookies
- **FR-004**: System MUST automatically refresh access tokens when expired using the refresh token
- **FR-005**: System MUST support token rotation on refresh (invalidate old refresh token, issue new one)
- **FR-006**: System MUST redirect users to login screen when authentication fails or session expires
- **FR-007**: System MUST extract user role and tenant information from JWT access token claims

#### Role-Based Access Control

- **FR-008**: System MUST support three user roles: superadmin, tenant_admin, standard
- **FR-009**: Superadmin users MUST see all tenants in a dropdown selector in the interface header
- **FR-010**: Superadmin users MUST be able to switch active tenant context from the dropdown
- **FR-011**: Tenant admin users MUST only access data within their own tenant (no tenant switcher)
- **FR-012**: Standard users MUST have screen-level permissions: disallowed, readonly, or full_crud
- **FR-013**: System MUST hide screens from navigation when user has "disallowed" permission
- **FR-014**: System MUST hide create/edit/delete buttons when user has "readonly" permission
- **FR-015**: System MUST include explicit tenant_id parameter in all API requests to backend

#### User Management

- **FR-016**: Superadmin and tenant admin users MUST be able to create new users
- **FR-017**: Superadmin users MUST be able to create users in any tenant
- **FR-018**: Tenant admin users MUST only be able to create users in their own tenant
- **FR-019**: System MUST validate email uniqueness when creating users
- **FR-020**: System MUST allow assigning one or more roles to users (superadmin, tenant_admin, standard, tenant)
- **FR-021**: System MUST display user status (active, disabled, invited, expired)
- **FR-022**: Users MUST be able to view their own profile information
- **FR-023**: System MUST allow superadmin and tenant admin to update user status
- **FR-024**: System MUST allow superadmin and tenant admin to disable users
- **FR-025**: System MUST implement soft-delete for users (disable instead of hard delete)

#### Tenant Management

- **FR-026**: Only superadmin users MUST be able to create new tenants
- **FR-027**: System MUST validate tenant name uniqueness when creating tenants
- **FR-028**: System MUST display tenant status (active, disabled, invited, expired)
- **FR-029**: System MUST allow superadmin to update tenant details (name, status)
- **FR-030**: System MUST allow superadmin to disable tenants
- **FR-031**: System MUST implement soft-delete for tenants (disable instead of hard delete)
- **FR-032**: System MUST show all users belonging to a tenant in the tenant detail view

#### Feature Flag Management

- **FR-033**: System MUST allow creating feature flags with name, flag_type, status, and values
- **FR-034**: System MUST enforce tenant_id scope for all feature flag operations
- **FR-035**: Superadmin users MUST be able to manage feature flags across all tenants
- **FR-036**: Tenant admin users MUST be able to manage feature flags within their own tenant
- **FR-037**: Standard users with appropriate permissions MUST be able to view feature flags
- **FR-038**: System MUST validate feature flag name uniqueness within tenant scope

#### Policy Management

- **FR-039**: System MUST allow creating authorization policies with conditions and verdicts
- **FR-040**: System MUST support policy verdicts: ALLOW, DENY, ABSTAIN
- **FR-041**: System MUST allow associating policies with specific actions and resources
- **FR-042**: Superadmin users MUST be able to manage policies across all tenants
- **FR-043**: Tenant admin users MUST be able to manage policies within their own tenant
- **FR-044**: System MUST validate policy syntax before saving

#### Invitation Management

- **FR-045**: System MUST allow creating invitations for new users with email and roles
- **FR-046**: System MUST generate unique invitation tokens with expiration timestamps
- **FR-047**: System MUST display invitation status (pending, accepted, expired, revoked)
- **FR-048**: System MUST allow superadmin and tenant admin to revoke pending invitations
- **FR-049**: System MUST enforce tenant_id scope for invitation operations

#### Audit Log Viewing

- **FR-050**: System MUST display audit events with actor, action, resource, tenant, and timestamp
- **FR-051**: System MUST allow filtering audit events by tenant_id, actor_id, action, and date range
- **FR-052**: Superadmin users MUST be able to view audit events across all tenants
- **FR-053**: Tenant admin users MUST only be able to view audit events within their own tenant
- **FR-054**: System MUST paginate audit log results (default 50 per page)

#### User Interface

- **FR-055**: System MUST display user-friendly error messages for all failed operations
- **FR-056**: System MUST show loading indicators during asynchronous operations
- **FR-057**: System MUST provide confirmation dialogs for destructive operations (disable, delete, revoke)
- **FR-058**: System MUST support pagination for all list views (users, tenants, feature flags, policies, invitations, audit events)
- **FR-059**: System MUST support filtering and sorting on list views
- **FR-060**: System MUST display success notifications after successful create/update/delete operations

### Non-Functional Requirements

- **NFR-001**: System MUST complete page load within 3 seconds on standard broadband connections
- **NFR-002**: System MUST complete API requests within 500ms at p95 for CRUD operations
- **NFR-003**: System MUST be responsive and usable on desktop browsers (1280x720 minimum resolution) and tablet devices in landscape mode (iPad 1024x768+, Android 960x600+)
- **NFR-004**: System MUST work in latest versions of Chrome, Firefox, Safari, and Edge browsers on desktop and tablet platforms
- **NFR-005**: System MUST maintain accessibility standards (WCAG 2.1 Level AA) for screen readers and keyboard navigation
- **NFR-006**: System MUST be embeddable in iframe contexts (Apache Superset, Power BI) for future extensions
- **NFR-007**: System MUST implement responsive design with fluid layouts adapting to viewport width, CSS media queries for breakpoints (768px, 1024px, 1280px), and touch-friendly UI elements with minimum 44px touch targets
- **NFR-008**: System MUST support touch gestures on tablet devices (tap, swipe for navigation, pinch-to-zoom where appropriate)

### Key Entities

- **User**: Represents an authenticated user with email, roles, tenant association, status, and audit timestamps. Users belong to exactly one tenant and have one or more roles that determine their permissions.

- **Tenant**: Represents an organization or customer account with unique name, status, and audit timestamps. Tenants contain users, feature flags, policies, invitations, and audit events. All operations are scoped by tenant_id.

- **FeatureFlag**: Represents a configurable feature toggle with name, type (boolean/string/number/json), status (enabled/disabled), and values. Feature flags are tenant-scoped and used to control application behavior.

- **Policy**: Represents an authorization rule with conditions and verdict (ALLOW/DENY/ABSTAIN). Policies define fine-grained access control for specific actions and resources within a tenant.

- **Invitation**: Represents a pending user invitation with email, roles, token, expiration timestamp, and status (pending/accepted/expired/revoked). Invitations are tenant-scoped and allow new users to join a tenant.

- **AuditEvent**: Represents a logged action with actor_id, action name, resource type, resource_id, tenant_id, timestamp, and optional event data. Audit events provide an immutable record of all system operations for compliance and troubleshooting.

## Architecture Decisions (Clarified)

### Q1: Frontend Framework Stack

**Decision**: React-admin framework using the marmelab demo template

**Rationale**: React-admin provides pre-built CRUD interfaces, authentication providers, and data providers that significantly accelerate development. The marmelab demo template offers a production-quality reference implementation with best practices for multi-tenant applications.

**Reference**: <https://github.com/marmelab/react-admin/tree/master/examples/demo>

### Q2: Authentication Flow

**Decision**: Hybrid JWT + HttpOnly refresh token approach

**Details**:

- Short-lived access token (15 minutes) stored in localStorage for API Authorization headers
- Long-lived refresh token (7 days) stored as HttpOnly, Secure, SameSite=None cookie
- Token rotation on refresh (old refresh token invalidated, new one issued)

**Rationale**:

- **XSS Protection**: HttpOnly refresh token not accessible to JavaScript
- **CSRF Mitigation**: Short-lived access tokens minimize attack window
- **Embed Mode Compatible**: SameSite=None; Secure cookies work in iframe contexts (Apache Superset, Power BI)
- **OWASP Compliance**: Follows OWASP recommendations for token-based authentication

### Q3: Deployment Strategy

**Decision**: Flexible deployment supporting separate repositories and build modes

**Development**:

- Separate repository: `githubspeckit-frontend`
- Independent development and extension by third parties

**Production Options**:

- **Low volume**: Monorepo build (backend serves static assets from `/static`)
- **High volume**: Distributed deployment (frontend CDN/container + backend API cluster)

**Backend Configuration**:

- Extended `DEPLOY_MODE` environment variable: `backend-only`, `monorepo`, `frontend-only`

### Q4: RBAC UI Permissions

**Decision**: Role-based permissions with screen-level granularity

**Roles**:

- **Superadmin**: Full CRUD across all tenants with tenant dropdown switcher
- **Tenant_admin**: Full CRUD within own tenant only (no tenant switcher)
- **Standard/Tenant users**: Three permission levels per screen:
  - `disallowed`: Screen hidden from navigation
  - `readonly`: View/list only, no create/edit/delete buttons
  - `full_crud`: All operations enabled

**Defense-in-Depth**: Backend validates every API call regardless of UI permission state

### Q5: Multi-Tenant Switching

**Decision**: Superadmin-only tenant dropdown + explicit tenant_id in API calls

**Implementation**:

- **Superadmin**: Dropdown in header to select active tenant context
- **All API calls**: Include explicit `?tenant_id={selected}` query parameter
- **Non-superadmin**: JWT tenant_id claim auto-filters (no switcher UI visible)

**Rationale**: Matches existing backend pattern from integration tests (test_tenant_isolation.py), ensures explicit tenant scoping for all operations, prevents accidental cross-tenant data access.

## Review & Acceptance Checklist

### Content Quality

- [x] No implementation details (languages, frameworks, APIs) - **Note: Architecture Decisions section includes chosen framework per clarification process, separated from requirements**
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders (requirements section)
- [x] All mandatory sections completed

### Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain - **All 5 clarification questions answered**
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (60 functional requirements with clear acceptance criteria)
- [x] Scope is clearly bounded (admin interface for 6 resource types across 3 user roles)
- [x] Dependencies and assumptions identified (backend REST API exists with 22 endpoints)

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted (5-question clarification session completed)
- [x] Ambiguities marked and resolved
- [x] User scenarios defined (6 acceptance scenarios, 6 edge cases)
- [x] Requirements generated (60 functional requirements, 6 non-functional requirements)
- [x] Entities identified (6 key entities: User, Tenant, FeatureFlag, Policy, Invitation, AuditEvent)
- [x] Review checklist passed

## Next Steps

1. **Generate Implementation Plan**: Run `/plan` command to create `specs/002-react-admin-frontend/plan.md` with technical architecture, project structure, and phased execution strategy
2. **Break Down Tasks**: Run `/tasks` command to create `specs/002-react-admin-frontend/tasks.md` with granular task lanes covering scaffolding, authentication, data providers, resource components, RBAC UI, multi-tenant switching, and testing
3. **Backend Integration**: Verify all 22 REST API endpoints are documented and accessible (auth, users, tenants, feature flags, policies, invitations, audit events, logs, metrics)
4. **Frontend Repository Setup**: Initialize separate `githubspeckit-frontend` repository with React-admin scaffolding

---
