# Tasks: React-Admin Frontend for Multi-Tenant Backend

**Input**: Design documents from `/specs/002-react-admin-frontend/`  
**Prerequisites**: plan.md ✅, research.md ✅  
**Branch**: `002-react-admin-frontend`  
**Repository**: Separate `githubspeckit-frontend` repository to be created

## Execution Flow

```text
1. ✅ Loaded plan.md: React-admin v4.16+, TypeScript 5.3+, Vite, 6 resources
2. ✅ Loaded research.md: 6 technical decisions documented
3. ✅ Generated 64 tasks across 11 phases (setup → tests → implementation → polish)
4. ✅ Applied TDD ordering: All contract/integration tests before implementation
5. ✅ Marked [P] for parallel execution: Different files, no dependencies
6. ✅ Validated: All resources have tests, responsive design included
7. SUCCESS: Tasks ready for execution
```

## Task Summary

- **Total Tasks**: 64
- **Estimated Effort**: 70-90 hours (3-4 weeks solo, 1.5 weeks team of 3)
- **Parallel Tasks**: 35 tasks marked [P] (can run simultaneously)
- **Critical Path**: T001-T005 (setup) → T006-T020 (tests) → T021-T055 (implementation) → T056-T064 (polish)

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **File paths**: Relative to `githubspeckit-frontend/` repository root

---

## Phase 3.1: Repository & Project Setup ✅ COMPLETE

**Objective**: Initialize separate frontend repository with Vite + React + TypeScript + React-admin

- [x] **T001** Create new repository `githubspeckit-frontend` (separate from backend monorepo)
  - Initialize git repository
  - Create `.gitignore` (node_modules, dist, .env.local)
  - Add LICENSE (match backend: MIT or Apache 2.0)
  - Create initial README.md with project overview

- [x] **T002** Initialize Vite + React + TypeScript project
  - Run: `npm create vite@latest . -- --template react-ts`
  - Configure `vite.config.ts` with proxy for local backend development
  - Set up `tsconfig.json` with strict mode enabled
  - Configure path aliases: `@/` → `src/`

- [x] **T003** Install core dependencies
  - Install: `react-admin@^4.16`, `ra-data-simple-rest@^4.16`
  - Install: `@mui/material@^5.14`, `@mui/icons-material@^5.14`
  - Install: `@tanstack/react-query@^5.0`
  - Install: `react-hook-form@^7.48`
  - Install: `axios@^1.6`
  - Install dev dependencies: `vitest@^1.0`, `@testing-library/react@^14.1`, `@testing-library/jest-dom@^6.1`, `msw@^2.0`

- [x] **T004** [P] Configure ESLint and Prettier
  - File: `eslint.config.js`
  - Enable TypeScript rules, React hooks rules
  - Configure Prettier integration (no semicolons, single quotes)
  - Add npm scripts: `lint`, `format`

- [x] **T005** [P] Configure environment variables
  - File: `.env.example` with template: `VITE_API_BASE_URL`, `VITE_DEPLOY_MODE`
  - File: `.env.development` with localhost backend URL
  - File: `src/config/env.ts` with type-safe environment variable loader
  - Validate no direct `import.meta.env` usage outside config module

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL**: All tests MUST be written and MUST FAIL before ANY implementation begins.

### Contract Tests (API Mocking with MSW) ✅ COMPLETE

- [x] **T006** [P] Setup MSW mock server configuration
  - File: `tests/mocks/server.ts`
  - Configure MSW v2 with REST handlers
  - Setup `beforeAll`, `afterEach`, `afterAll` hooks for Vitest
  - File: `tests/setup.ts` with MSW server initialization

- [x] **T007** [P] Create MSW handlers for auth endpoints
  - File: `tests/mocks/handlers/auth.ts`
  - Mock: `POST /api/v1/auth/login` → return access_token + user object
  - Mock: `POST /api/v1/auth/refresh` → return new access_token
  - Mock: `POST /api/v1/auth/logout` → return 204 No Content
  - Include error scenarios: 401 invalid credentials, 403 forbidden

- [x] **T008** [P] Create MSW handlers for users endpoints
  - File: `tests/mocks/handlers/users.ts`
  - Mock: `GET /api/v1/users?tenant_id={id}` → return paginated user list
  - Mock: `GET /api/v1/users/:id?tenant_id={id}` → return single user
  - Mock: `POST /api/v1/users?tenant_id={id}` → return created user
  - Mock: `PUT /api/v1/users/:id?tenant_id={id}` → return updated user
  - Mock: `DELETE /api/v1/users/:id?tenant_id={id}` → return 204
  - Mock: `GET /api/v1/users/me` → return current user
  - Verify tenant_id injection in all requests (except /me)

- [x] **T009** [P] Create MSW handlers for tenants endpoints
  - File: `tests/mocks/handlers/tenants.ts`
  - Mock: `GET /api/v1/tenants` → return tenant list (superadmin only)
  - Mock: `GET /api/v1/tenants/:id` → return single tenant
  - Mock: `POST /api/v1/tenants` → return created tenant
  - Mock: `PUT /api/v1/tenants/:id` → return updated tenant
  - Mock: `DELETE /api/v1/tenants/:id` → return 204
  - Mock: `POST /api/v1/tenants/:id/restore` → return restored tenant

- [x] **T010** [P] Create MSW handlers for feature flags, policies, invitations, audit events
  - File: `tests/mocks/handlers/featureFlags.ts` (GET, POST, PUT, DELETE with tenant_id)
  - File: `tests/mocks/handlers/policies.ts` (GET, POST, PUT, DELETE with tenant_id)
  - File: `tests/mocks/handlers/invitations.ts` (GET, POST, GET/:id, POST/:id/revoke with tenant_id)
  - File: `tests/mocks/handlers/auditEvents.ts` (GET with filters: tenant_id, actor_id, action, date range)

### Integration Tests (User Journeys) ✅ COMPLETE

- [x] **T011** [P] Integration test: Superadmin login & tenant switching
  - File: `tests/integration/auth-superadmin.test.tsx`
  - Test Scenario 1 from quickstart.md (in plan.md Phase 1)
  - Assert: Login succeeds, tenant dropdown visible, tenant switch changes API tenant_id param
  - Assert: Create user in selected tenant includes correct tenant_id

- [x] **T012** [P] Integration test: Tenant admin user management
  - File: `tests/integration/auth-tenant-admin.test.tsx`
  - Test Scenario 2 from quickstart.md
  - Assert: Login succeeds, no tenant dropdown, tenant_id fixed in API calls
  - Assert: Tenants menu hidden (403)

- [x] **T013** [P] Integration test: Standard user limited access
  - File: `tests/integration/rbac-standard-user.test.tsx`
  - Test Scenario 3 from quickstart.md
  - Assert: Only permitted resources in menu
  - Assert: Readonly permissions hide Create/Edit/Delete buttons
  - Assert: Disallowed resources redirect to 403

- [x] **T014** [P] Integration test: Token refresh transparency
  - File: `tests/integration/auth-token-refresh.test.tsx`
  - Test Scenario 4 from quickstart.md
  - Mock: Token expires after 2 minutes
  - Assert: API call triggers refresh, succeeds without login redirect
  - Assert: New access token stored in localStorage

- [x] **T015** [P] Integration test: Logout & session cleanup
  - File: `tests/integration/auth-logout.test.tsx`
  - Test Scenario 5 from quickstart.md
  - Assert: Logout clears localStorage, calls backend /logout
  - Assert: Redirect to login, protected routes inaccessible

- [x] **T016** [P] Integration test: Tablet responsive layout
  - File: `tests/integration/responsive-tablet.test.tsx`
  - Test Scenario 6 from quickstart.md
  - Mock: Viewport 1024x768 (iPad landscape)
  - Assert: SimpleList renders on tablet (not Datagrid)
  - Assert: All buttons/inputs ≥44px touch targets (measure via DOM query)
  - Assert: Form fields stack in responsive grid
  - Mock: Viewport 1280x1024 (desktop)
  - Assert: Datagrid renders with all columns

### Component Tests (AuthProvider & DataProvider) ✅ COMPLETE

- [x] **T017** [P] Component test: authProvider.login()
  - File: `tests/components/authProvider.test.ts`
  - Assert: POST /api/v1/auth/login with email/password
  - Assert: access_token stored in localStorage
  - Assert: user object stored in localStorage

- [x] **T018** [P] Component test: authProvider.checkAuth()
  - File: `tests/components/authProvider.test.ts`
  - Assert: Returns resolved promise if access_token exists
  - Assert: Returns rejected promise if no token → redirect to login

- [x] **T019** [P] Component test: authProvider.checkError() 401 handling
  - File: `tests/components/authProvider.test.ts`
  - Assert: 401 response triggers token refresh attempt
  - Assert: Refresh success → retry original request
  - Assert: Refresh failure → redirect to login, clear localStorage

- [x] **T020** [P] Component test: dataProvider with tenant_id injection
  - File: `tests/components/dataProvider.test.ts`
  - Test: getList('users') for superadmin → includes ?tenant_id={selected}
  - Test: getList('users') for tenant_admin → includes ?tenant_id={jwt_claim}
  - Test: getOne, create, update, delete → all include tenant_id
  - Assert: GET /api/v1/users/me does NOT include tenant_id

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### TypeScript Type Definitions

- [x] **T021** [P] Create User type definitions
  - File: `src/types/user.ts`
  - Interface: `User { user_id, tenant_id, email, roles, status, created_at, updated_at }`
  - Type: `UserRole = 'superadmin' | 'tenant_admin' | 'standard'`
  - Type: `UserStatus = 'invited' | 'active' | 'disabled'`

- [x] **T022** [P] Create Tenant, FeatureFlag, Policy, Invitation, AuditEvent types
  - File: `src/types/tenant.ts` → `Tenant { tenant_id, name, status, config_version, created_at, updated_at }`
  - File: `src/types/featureFlag.ts` → `FeatureFlag { flag_id, tenant_id, name, flag_type, status, values, created_at, updated_at }`
  - File: `src/types/policy.ts` → `Policy { policy_id, tenant_id, resource_type, action, effect, conditions, created_at, updated_at }`
  - File: `src/types/invitation.ts` → `Invitation { invitation_id, tenant_id, email, roles, status, expires_at, created_at }`
  - File: `src/types/auditEvent.ts` → `AuditEvent { event_id, tenant_id, actor_id, action, resource_type, resource_id, timestamp, metadata }`

- [x] **T023** [P] Create Auth types
  - File: `src/types/auth.ts`
  - Interface: `LoginRequest { email, password }`
  - Interface: `LoginResponse { access_token, token_type, expires_in, user: User }`
  - Interface: `RefreshResponse { access_token, expires_in }`

- [x] **T024** [P] Create Permission types
  - File: `src/types/permissions.ts`
  - Type: `PermissionLevel = 'allowed' | 'disallowed' | 'readonly'`
  - Interface: `ResourcePermission { resource: string, action: string, permission: PermissionLevel }`
  - Interface: `RolePermissions { role: string, permissions: ResourcePermission[] }`

### Configuration & Utilities

- [x] **T025** [P] Create environment configuration module
  - File: `src/config/env.ts`
  - Export: `API_BASE_URL` from `VITE_API_BASE_URL`
  - Export: `DEPLOY_MODE` from `VITE_DEPLOY_MODE`
  - Validate required variables at import time

- [x] **T026** [P] Create API client wrapper with interceptors
  - File: `src/utils/api.ts`
  - Configure axios instance with `API_BASE_URL`
  - Request interceptor: Inject `Authorization: Bearer {token}` header
  - Response interceptor: Handle 401 → trigger token refresh → retry original request
  - Response interceptor: Handle 403, 500 → format user-friendly error messages

- [x] **T027** [P] Create localStorage abstraction
  - File: `src/utils/storage.ts`
  - Functions: `getAccessToken()`, `setAccessToken(token)`, `clearAuth()`
  - Functions: `getUser()`, `setUser(user)`, `clearUser()`
  - Type-safe wrappers around localStorage with JSON parsing

- [x] **T028** [P] Create permission helper functions
  - File: `src/utils/permissions.ts`
  - Function: `getPermissionForResource(role, resource, action): PermissionLevel`
  - Constant: `ROLE_PERMISSIONS` mapping (superadmin → all allowed, tenant_admin → limited, standard → readonly)
  - Function: `canAccess(role, resource, action): boolean`

### Providers (React-admin Core)

- [x] **T029** Implement authProvider
  - File: `src/providers/authProvider.ts`
  - Implement: `login({ email, password })` → POST /api/v1/auth/login, store token + user
  - Implement: `logout()` → POST /api/v1/auth/logout, clear localStorage
  - Implement: `checkAuth()` → validate token exists (no API call, fast check)
  - Implement: `checkError(error)` → if 401, attempt refresh; if refresh fails, reject
  - Implement: `getPermissions()` → return user roles from localStorage
  - Implement: `getIdentity()` → return user object from localStorage

- [x] **T030** Implement token refresh logic in authProvider
  - File: `src/providers/authProvider.ts` (extend T029)
  - Function: `refreshAccessToken()` → POST /api/v1/auth/refresh (HttpOnly cookie sent automatically)
  - On success: Update localStorage access_token, return new token
  - On failure: Clear auth, return rejected promise → redirect to login

- [x] **T031** Implement dataProvider with tenant_id injection
  - File: `src/providers/dataProvider.ts`
  - Wrap: `simpleRestProvider(API_BASE_URL)` from `ra-data-simple-rest`
  - Middleware: Inject `?tenant_id={id}` query param in all requests
  - Get tenant_id: If superadmin → from TenantContext, else → from user.tenant_id in localStorage
  - Exception: GET /api/v1/users/me should NOT include tenant_id

### Contexts (Tenant Switching for Superadmin)

- [x] **T032** [P] Create TenantContext provider
  - File: `src/contexts/TenantContext.tsx`
  - State: `selectedTenantId`, `setSelectedTenantId`
  - Effect: On tenant change, refresh data (trigger react-query refetch)
  - Export: `useTenant()` hook for accessing context

- [x] **T033** [P] Create TenantSwitcher component
  - File: `src/components/TenantSwitcher/TenantSwitcher.tsx`
  - Props: List of tenants (fetch from GET /api/v1/tenants)
  - Render: Material-UI Select dropdown with tenant names
  - On change: Call `setSelectedTenantId()` from TenantContext
  - Visibility: Only render if user role is 'superadmin'
  - Responsive: Adjust width based on viewport (150px tablet, 200px desktop)

### Layout Components

- [x] **T034** [P] Create custom AppBar with TenantSwitcher
  - File: `src/components/layout/AppBar.tsx`
  - Extend: `<AppBar>` from react-admin
  - Add: `<TenantSwitcher>` in header (right side, before user menu)
  - Conditional render: Only show if user role is 'superadmin'

- [x] **T035** [P] Create custom Layout
  - File: `src/components/layout/Layout.tsx`
  - Compose: `<Layout appBar={CustomAppBar}>` from react-admin
  - Configure responsive menu (collapsed on tablet)

- [x] **T036** [P] Create Error Boundary component
  - File: `src/components/layout/ErrorBoundary.tsx`
  - Catch: React errors, display user-friendly message
  - Log: Error details to console (future: send to error tracking service)
  - Fallback: Show "Something went wrong" with reload button

- [x] **T037** [P] Create 403 Forbidden page
  - File: `src/components/layout/ForbiddenPage.tsx`
  - Display: "You don't have permission to access this resource"
  - Button: "Go to Dashboard"

### Resource Components (6 Resources × CRUD)

#### Users Resource

- [x] **T038** [P] Implement UserList component
  - File: `src/resources/users/UserList.tsx`
  - Responsive: `useMediaQuery(breakpoints.down('lg'))` → SimpleList on tablet, Datagrid on desktop
  - Datagrid columns: email, roles (ChipField), status, created_at
  - SimpleList: primaryText=email, secondaryText=roles + status
  - Filters: status, roles, search by email
  - Bulk actions: Enable/Disable users

- [x] **T039** [P] Implement UserCreate component
  - File: `src/resources/users/UserCreate.tsx`
  - Form fields: email (TextInput), roles (SelectArrayInput), status (SelectInput)
  - Validation: Email format, required fields
  - Responsive: Grid layout (xs=12, md=6 for side-by-side on desktop)

- [x] **T040** [P] Implement UserEdit component
  - File: `src/resources/users/UserEdit.tsx`
  - Same fields as UserCreate
  - Show: created_at, updated_at (read-only)

- [x] **T041** [P] Implement UserShow component
  - File: `src/resources/users/UserShow.tsx`
  - Display all user fields (read-only)
  - Show related data: Last login, invitation history (future)

#### Tenants Resource

- [x] **T042** [P] Implement TenantList component (superadmin only)
  - File: `src/resources/tenants/TenantList.tsx`
  - Datagrid columns: name, status, config_version, created_at
  - Filters: status, search by name
  - Actions: Enable/Disable, Restore deleted tenants

- [x] **T043** [P] Implement TenantCreate, TenantEdit, TenantShow components
  - File: `src/resources/tenants/TenantCreate.tsx`
  - File: `src/resources/tenants/TenantEdit.tsx`
  - File: `src/resources/tenants/TenantShow.tsx`
  - Fields: name, status, config_version (auto-incremented on update)

#### Feature Flags Resource

- [x] **T044** [P] Implement FeatureFlagList, Create, Edit, Show components
  - File: `src/resources/featureFlags/FeatureFlagList.tsx`
  - File: `src/resources/featureFlags/FeatureFlagCreate.tsx`
  - File: `src/resources/featureFlags/FeatureFlagEdit.tsx`
  - File: `src/resources/featureFlags/FeatureFlagShow.tsx`
  - Fields: name, flag_type (boolean/string/number/json), status (enabled/disabled), values (JSON editor)
  - Responsive: SimpleList on tablet, Datagrid on desktop

#### Policies Resource

- [x] **T045** [P] Implement PolicyList, Create, Edit, Show components
  - File: `src/resources/policies/PolicyList.tsx`
  - File: `src/resources/policies/PolicyCreate.tsx`
  - File: `src/resources/policies/PolicyEdit.tsx`
  - File: `src/resources/policies/PolicyShow.tsx`
  - Fields: resource_type, action, effect (ALLOW/DENY/ABSTAIN), conditions (JSON editor)
  - Complex: JSON editor for conditions field

#### Invitations Resource

- [x] **T046** [P] Implement InvitationList, Create, Show components (no Edit)
  - File: `src/resources/invitations/InvitationList.tsx`
  - File: `src/resources/invitations/InvitationCreate.tsx`
  - File: `src/resources/invitations/InvitationShow.tsx`
  - Fields: email, roles, status (pending/accepted/expired/revoked), expires_at
  - Actions: Revoke invitation (custom button calling POST /api/v1/invitations/:id/revoke)

#### Audit Events Resource

- [x] **T047** [P] Implement AuditEventList component (read-only, no create/edit/delete)
  - File: `src/resources/auditEvents/AuditEventList.tsx`
  - Datagrid columns: timestamp, actor_id, action, resource_type, resource_id
  - Filters: tenant_id, actor_id, action, date range (DateInput)
  - Export: CSV export button for compliance reports

### RBAC & Permission Enforcement

- [x] **T048** Configure resource permissions in App.tsx
  - File: `src/App.tsx`
  - Map resources to roles: superadmin (all), tenant_admin (users, featureFlags, policies, invitations, auditEvents), standard (auditEvents readonly)
  - Hide resources based on `getPermissions()` return value
  - Disable buttons: Edit/Delete buttons hidden if permission = 'readonly'

- [x] **T049** [P] Create custom resource registration with permissions
  - File: `src/utils/resourceRegistration.ts`
  - Function: `registerResource(name, permissions)` → return Resource component with conditional list/create/edit/show
  - Use in App.tsx for all 6 resources

### Responsive Design (Tablet Support)

- [x] **T050** Configure Material-UI theme with responsive breakpoints
  - File: `src/App.tsx` (extend T048)
  - Set breakpoints: xs=0, sm=600, md=960, lg=1280, xl=1920
  - Set spacing: 8px base (44px touch target = 5.5 * spacing)
  - Override components: MuiButton, MuiIconButton → minHeight: 44px, minWidth: 44px

- [x] **T051** [P] Implement responsive form layouts with Grid
  - Apply to: UserCreate, UserEdit, TenantCreate, TenantEdit, FeatureFlagCreate, PolicyCreate
  - Pattern: `<Grid item xs={12} md={6}>` for side-by-side on desktop, stacked on tablet

- [x] **T052** [P] Add viewport meta tag for tablet scaling
  - File: `public/index.html`
  - Tag: `<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">`

### App Entry Point

- [x] **T053** Create main App component
  - File: `src/App.tsx`
  - Compose: `<Admin authProvider dataProvider i18nProvider theme layout>`
  - Register 6 resources: users, tenants, featureFlags, policies, invitations, auditEvents
  - Wrap in: `<TenantContext.Provider>` for superadmin tenant switching
  - Wrap in: `<ErrorBoundary>` for global error handling

- [x] **T054** Create entry point
  - File: `src/main.tsx`
  - Render: `<React.StrictMode><App /></React.StrictMode>`
  - Import: Global CSS (Material-UI baseline)

---

## Phase 3.4: Integration & Polish

### Build & Deployment Configuration

- [ ] **T055** Configure Vite build for production
  - File: `vite.config.ts`
  - Set base URL based on `DEPLOY_MODE` env var
  - Optimize: Code splitting, tree shaking, minification
  - Output: `dist/` directory with static assets

- [ ] **T056** [P] Create deployment mode configuration
  - File: `.env.production`
  - Document: Two modes (monorepo build vs distributed CDN)
  - If `DEPLOY_MODE=monorepo`: Backend serves from `/static`
  - If `DEPLOY_MODE=distributed`: CDN serves, CORS configured

- [ ] **T057** [P] Update README.md with setup instructions
  - File: `README.md`
  - Sections: Prerequisites, Installation, Development, Testing, Build, Deployment
  - Include: Environment variable configuration guide
  - Include: Backend API setup instructions (link to backend repo)

### Testing & Quality Assurance

- [ ] **T058** [P] Write unit tests for utility functions
  - File: `tests/unit/permissions.test.ts` → test `canAccess()`, `getPermissionForResource()`
  - File: `tests/unit/storage.test.ts` → test localStorage wrappers
  - File: `tests/unit/api.test.ts` → test axios interceptors (mock axios)

- [ ] **T059** Run all integration tests (validate T011-T016 pass)
  - Command: `npm run test:integration`
  - Assert: All 6 user journey scenarios pass
  - Assert: Auth flows, RBAC enforcement, tenant switching, token refresh, responsive layout all verified

- [ ] **T060** [P] Performance validation against budgets
  - Test: Initial page load <3s (Lighthouse CI)
  - Test: API request p95 <500ms (MSW timing simulation)
  - Test: React component render <16ms (React DevTools Profiler)
  - Test: Bundle size <500KB gzipped (Vite build report)
  - Document: Baseline metrics in `docs/performance.md`

- [ ] **T061** [P] Accessibility validation (WCAG 2.1 AA)
  - Tool: axe DevTools browser extension
  - Test: Keyboard navigation (Tab, Enter, Esc)
  - Test: Screen reader compatibility (NVDA/JAWS)
  - Test: Color contrast ratios ≥4.5:1
  - Test: Touch target sizes ≥44px (tablet)
  - Fix: Any violations found

- [ ] **T062** [P] Security validation
  - Test: XSS prevention (try injecting `<script>` in form fields, verify escaped)
  - Test: Token handling (verify no access_token in URL, network logs, or XHR responses visible to non-dev users)
  - Test: CSRF mitigation (verify SameSite cookie, short-lived access token)
  - Test: Dependency scan (`npm audit`, address high/critical vulnerabilities)

### Documentation & Handoff

- [ ] **T063** [P] Create quickstart.md in repository
  - File: `docs/quickstart.md`
  - Copy 6 scenarios from plan.md Phase 1
  - Add: Screenshots or screen recordings for each scenario
  - Add: Expected outcomes and troubleshooting tips

- [ ] **T064** Execute manual validation of all quickstart scenarios
  - Run: Each scenario from T063 on local environment
  - Verify: All assertions pass, no console errors
  - Document: Any deviations or known issues in `docs/known-issues.md`

---

## Dependencies Graph

```text
Setup Phase (T001-T005)
  ↓
Tests Phase (T006-T020) [All tests must FAIL before continuing]
  ↓
Core Implementation (T021-T054)
  ├─ Types (T021-T024) [P] → No dependencies
  ├─ Config/Utils (T025-T028) [P] → No dependencies
  ├─ Providers (T029-T031) → Depends on T025-T028
  ├─ Contexts (T032-T033) [P] → Depends on T031
  ├─ Layout (T034-T037) [P] → Depends on T033
  ├─ Resources (T038-T047) [P] → Depends on T029-T031
  ├─ RBAC (T048-T049) → Depends on T038-T047
  ├─ Responsive (T050-T052) [P] → Depends on T034-T047
  └─ App (T053-T054) → Depends on all above
  ↓
Integration & Polish (T055-T064)
  ├─ Build (T055-T057) [P] → Depends on T053-T054
  ├─ Testing (T058-T062) [P] → Depends on T053-T054
  └─ Documentation (T063-T064) → Depends on all tests passing
```

## Parallel Execution Examples

### Example 1: Type Definitions (After T020 tests pass)

```bash
# Launch T021-T024 together (different files, no dependencies):
Task T021: "Create User type definitions in src/types/user.ts"
Task T022: "Create Tenant type in src/types/tenant.ts"
Task T022: "Create FeatureFlag type in src/types/featureFlag.ts"
Task T022: "Create Policy type in src/types/policy.ts"
Task T022: "Create Invitation type in src/types/invitation.ts"
Task T022: "Create AuditEvent type in src/types/auditEvent.ts"
Task T023: "Create Auth types in src/types/auth.ts"
Task T024: "Create Permission types in src/types/permissions.ts"
```

### Example 2: Resource Components (After T031 dataProvider)

```bash
# Launch T038-T047 together (different resource directories):
Task T038: "Implement UserList in src/resources/users/UserList.tsx"
Task T042: "Implement TenantList in src/resources/tenants/TenantList.tsx"
Task T044: "Implement FeatureFlagList in src/resources/featureFlags/FeatureFlagList.tsx"
Task T045: "Implement PolicyList in src/resources/policies/PolicyList.tsx"
Task T046: "Implement InvitationList in src/resources/invitations/InvitationList.tsx"
Task T047: "Implement AuditEventList in src/resources/auditEvents/AuditEventList.tsx"
```

### Example 3: Quality Assurance (After T054 implementation)

```bash
# Launch T058, T060-T062 together (independent validation):
Task T058: "Write unit tests for utils in tests/unit/"
Task T060: "Performance validation (Lighthouse CI)"
Task T061: "Accessibility validation (axe DevTools)"
Task T062: "Security validation (XSS, token handling, npm audit)"
```

---

## Validation Checklist

**GATE**: Verify before marking tasks complete

- [x] All MSW handlers created for 22 API endpoints (T007-T010)
- [x] All 6 user journey integration tests written (T011-T016)
- [x] All 6 resources have List, Create, Edit, Show components (T038-T047)
- [x] All tests come before implementation (T006-T020 before T021-T054)
- [x] Parallel tasks [P] are truly independent (different files)
- [x] No [P] task modifies same file as another [P] task
- [x] Each task specifies exact file path
- [x] Responsive design included (T050-T052 tablet support)
- [x] RBAC permissions configured (T048-T049)
- [x] Token refresh logic implemented (T030)
- [x] Tenant context switching for superadmin (T032-T033)

---

## Notes

- **TDD Enforcement**: T006-T020 must ALL be failing before any T021+ implementation begins
- **Separate Repository**: Tasks assume `githubspeckit-frontend` as new repo (not subfolder of backend monorepo)
- **Backend Dependency**: Frontend requires backend running on `http://localhost:8000` for local development (use MSW mocks if backend unavailable)
- **Commit Strategy**: Commit after each task (or logical group of [P] tasks)
- **React-admin Version**: Pin to `4.16.x` to avoid breaking changes (upgrade carefully after MVP)
- **Material-UI**: Version 5.14+ included with react-admin, no separate install needed
- **Tablet Testing**: Use real iPad Safari and Android Chrome for final validation (T064), not just browser DevTools responsive mode
- **Token Refresh**: Test with short expiration (2 min) in dev, use 15 min in production
- **CORS**: Backend must set `Access-Control-Allow-Credentials: true` for HttpOnly refresh cookie
- **CSP**: Backend should set `Content-Security-Policy` headers for XSS protection
- **Future Enhancements**: PWA, i18n, dark mode, analytics (YAGNI for MVP)

---

**Status**: ✅ Ready for execution  
**Next Command**: `/task T001` to begin repository setup
