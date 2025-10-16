# Implementation Plan: React-Admin Frontend for Multi-Tenant Backend

**Branch**: `002-react-admin-frontend` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-react-admin-frontend/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

This feature delivers a production-ready React-admin web application providing administrative interfaces for the multi-tenant FastAPI backend. The frontend supports three role tiers (superadmin, tenant_admin, standard) with screen-level RBAC permissions, hybrid JWT authentication (localStorage access token + HttpOnly refresh cookie), and flexible deployment modes (separate repository for development, monorepo or distributed for production). The application manages six core resource types: Users, Tenants, Feature Flags, Policies, Invitations, and Audit Events, with explicit tenant_id scoping in all API calls.

**Primary Requirement**: Create admin UI enabling role-based CRUD operations across multi-tenant resources with secure authentication, tenant isolation, and embed compatibility (future Apache Superset/Power BI integration).

**Technical Approach**: React-admin framework (marmelab demo template reference), TypeScript, Vite build tool, REST dataProvider with tenant_id injection, authProvider implementing hybrid token strategy, role-based menu/button visibility, superadmin tenant switcher component.

## Technical Context

**Language/Version**: TypeScript 5.3+, React 18+, Node.js 20 LTS  
**Primary Dependencies**:

- react-admin ^4.16 (admin framework)
- react ^18.2 (UI library)
- vite ^5.0 (build tool)
- @tanstack/react-query ^5.0 (data fetching)
- react-hook-form ^7.48 (form handling)
- vitest ^1.0 (unit testing)
- @testing-library/react ^14.1 (component testing)
- axios or fetch API (HTTP client)
  
**Storage**: N/A (frontend consumes REST API; no direct database access)  

**Testing**: Vitest (unit tests), @testing-library/react (component tests), MSW (Mock Service Worker for API mocking), Playwright or Cypress (optional E2E)  

**Target Platform**: 
- Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Desktop: 1280x720 minimum, optimized for 1920x1080
- **Tablet**: iPad (landscape 1024x768+) and Android tablets (landscape 960x600+)
- **Responsive Design**: Fluid layouts adapting to viewport width, touch-friendly controls for tablets
- Mobile phones: Out of scope (admin interface not optimized for <768px screens)

**Project Type**: Web application (frontend only; backend exists at `/src` in parent monorepo)  

**Performance Goals**:

- Initial page load <3s on standard broadband (10 Mbps)
- API request p95 <500ms (backend responsibility; frontend caching/optimistic updates)
- React component render <16ms (60fps interaction)
- Bundle size <500KB gzipped (main chunk)
- Lighthouse performance score >90

**Constraints**: 

- MUST work in iframe contexts (SameSite=None; Secure cookies)
- MUST NOT expose access tokens in URLs or logs
- MUST handle token refresh transparently without user re-authentication
- MUST enforce backend RBAC (no client-only security assumptions)
- MUST support offline detection with graceful degradation
- MUST comply with WCAG 2.1 Level AA accessibility standards
- **MUST support tablet devices in landscape mode** (iPad 1024x768+, Android 960x600+)
- **MUST implement responsive design** with fluid layouts, flexible grid systems, and touch-friendly UI elements (44px minimum touch targets)**Scale/Scope**:

- 10-50 concurrent admin users per tenant (typical)
- 6 primary resource screens (Users, Tenants, Feature Flags, Policies, Invitations, Audit Events)
- ~15-20 React components (resources, layouts, auth, tenant switcher, error boundaries)
- ~30-40 unit/component tests
- ~10 integration tests (auth flows, RBAC enforcement, tenant switching)
- Estimated 5,000-8,000 LOC (TypeScript + JSX)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Check Status**: ✅ PASS (2025-10-12)

### Constitutional Evaluation for Frontend

1. **✅ Architecture (Principle I)**: COMPLIANT - Frontend follows component/service separation. React components are framework-specific (acceptable for UI), but business logic (dataProvider, authProvider, tenant context) isolated in service layer. No backend domain imports.

2. **✅ Test-First & Coverage (Principle II)**: COMPLIANT - Plan includes failing tests first approach. Target: ≥85% overall frontend coverage, 100% auth/RBAC critical paths (authProvider, tenant context injection, token refresh). Contract tests for all API integrations via MSW mocks.

3. **✅ Multi-Tenancy (Principles I & III)**: COMPLIANT - Every dataProvider API call includes explicit `?tenant_id={selected}` query parameter. Tenant context managed via React Context Provider. Non-superadmin calls auto-inject JWT tenant_id claim. No cross-tenant data access possible from UI.

4. **✅ RBAC & Policies (Principles III & VI)**: COMPLIANT - Authorization enforced by backend (defense-in-depth). Frontend implements UI-level role checks (hide menus/buttons) via permission configuration mapped to user roles. No inline role checks in components; permissions declared in resource configuration objects.

5. **✅ Auth Reuse (Principle VI)**: N/A - Frontend consumes backend `/v1/auth/*` endpoints; does not implement auth core. AuthProvider acts as adapter to backend auth system.

6. **✅ Switchable Persistence (Principle IV)**: N/A - Frontend has no persistence layer; all data fetched via REST API. DataProvider interface allows swapping API client (axios vs fetch) if needed.

7. **✅ Observability (Principle V)**: COMPLIANT - Client-side error tracking (React Error Boundaries + error reporting service integration point). Performance metrics via browser Performance API. Console logs structured with correlation_id forwarded from backend responses. Export not applicable (browser context).

8. **✅ API Versioning (Principle V)**: COMPLIANT - All API calls target `/api/v1/*` endpoints. Version included in dataProvider base URL configuration. Future versions handled via environment variable or runtime config.

9. **✅ Performance Budgets (Principle V)**: COMPLIANT - Declared in Technical Context: <3s initial load, <500ms API p95, <16ms render, <500KB bundle, Lighthouse >90. Baseline metrics captured in Phase 1 quickstart.

10. **✅ Unified Configuration (Principle VII)**: COMPLIANT - Single `.env` file with `VITE_` prefix for frontend vars. Build validates no `BACKEND_` tokens in bundle. DEPLOY_MODE env var controls static asset serving strategy (separate repo vs monorepo build). No direct `import.meta.env` access outside config module.

11. **✅ Developer Experience & Embed (Principle VIII)**: COMPLIANT - `npm run dev` starts Vite dev server with MSW API mocks (no backend required for UI development). Embed readiness: cookies configured with `SameSite=None; Secure`, CORS headers validated. Session continuity via token refresh endpoint.

12. **✅ Complexity (Governance & Principle IV)**: COMPLIANT - React-admin chosen over custom framework (proven solution, reduces complexity). No custom state management beyond React Query (included with react-admin). No premature abstractions (e.g., custom component library).

13. **✅ Security Testing (Additional Constraints & Principle V)**: COMPLIANT - XSS prevention via React auto-escaping + CSP headers. Token handling tests verify no exposure in URLs/localStorage. CSRF mitigation via double-submit token or backend validation. Dependency scan (npm audit) in CI. OWASP Top 10 mapped to frontend risks (A03:Injection, A05:Security Misconfiguration, A07:XSS).

14. **✅ Code Quality & Simplicity (Principle IX)**: COMPLIANT - TypeScript strict mode enforced. ESLint + Prettier for consistency. DRY: shared components in `/components/common`. KISS: prefer react-admin built-ins over custom implementations. YAGNI: no features beyond 6 core resources until validated need. Max component LOC: 200 (soft limit).

**Result**: All 14 constitutional principles evaluated. No violations. Frontend architecture aligns with backend constitutional guarantees through API contract compliance and explicit tenant/role scoping.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (separate frontend repository)

**Repository**: `githubspeckit-frontend` (new separate repository)

```text
githubspeckit-frontend/
├── public/
│   ├── favicon.ico
│   └── index.html
├── src/
│   ├── components/           # Shared UI components
│   │   ├── common/           # Buttons, inputs, cards, etc.
│   │   ├── layout/           # AppBar, Menu, Layout components
│   │   └── TenantSwitcher/   # Superadmin tenant dropdown
│   ├── resources/            # React-admin resource components
│   │   ├── users/            # User list/create/edit/show
│   │   ├── tenants/          # Tenant CRUD
│   │   ├── featureFlags/     # Feature flag management
│   │   ├── policies/         # Policy CRUD
│   │   ├── invitations/      # Invitation management
│   │   └── auditEvents/      # Audit log viewer (read-only)
│   ├── providers/            # React-admin providers
│   │   ├── authProvider.ts   # Auth logic (login, logout, getPermissions)
│   │   ├── dataProvider.ts   # REST API client with tenant_id injection
│   │   └── i18nProvider.ts   # Internationalization (future)
│   ├── contexts/             # React contexts
│   │   └── TenantContext.tsx # Current tenant state (superadmin switching)
│   ├── types/                # TypeScript type definitions
│   │   ├── user.ts
│   │   ├── tenant.ts
│   │   ├── featureFlag.ts
│   │   ├── policy.ts
│   │   ├── invitation.ts
│   │   └── auditEvent.ts
│   ├── config/               # Configuration module
│   │   └── env.ts            # VITE_ environment variable loader
│   ├── utils/                # Utility functions
│   │   ├── api.ts            # Axios/fetch wrapper with interceptors
│   │   ├── permissions.ts    # Permission check helpers
│   │   └── storage.ts        # localStorage abstraction
│   ├── App.tsx               # Main App component with react-admin <Admin>
│   ├── main.tsx              # Entry point
│   └── vite-env.d.ts         # Vite type declarations
├── tests/
│   ├── setup.ts              # Test configuration (MSW, vitest setup)
│   ├── mocks/                # MSW handlers for API mocking
│   │   ├── handlers.ts       # All API route handlers
│   │   └── server.ts         # MSW server setup
│   ├── unit/                 # Unit tests (utils, helpers)
│   │   ├── permissions.test.ts
│   │   └── storage.test.ts
│   ├── components/           # Component tests
│   │   ├── TenantSwitcher.test.tsx
│   │   └── authProvider.test.ts
│   └── integration/          # Integration tests (E2E flows)
│       ├── auth.test.ts      # Login, logout, token refresh
│       ├── rbac.test.ts      # Role-based UI visibility
│       └── tenantSwitching.test.ts  # Superadmin context switching
├── .env.example              # Environment variable template
├── .env.development          # Local dev configuration
├── .env.production           # Production build configuration
├── .gitignore
├── package.json              # Dependencies + scripts
├── tsconfig.json             # TypeScript configuration (strict mode)
├── vite.config.ts            # Vite build configuration
├── vitest.config.ts          # Vitest test configuration
├── eslint.config.js          # ESLint rules
└── README.md                 # Setup instructions
```

**Structure Decision**: Separate frontend repository (`githubspeckit-frontend`) for independent development and third-party extensibility. React-admin resource-based structure with providers following framework conventions. TypeScript strict mode for type safety. Vite for fast builds and HMR. MSW (Mock Service Worker) for API mocking in tests and local development.

**Backend Reference**: Existing backend at `/Users/sujoymukherjee/code/githubspeckit/src` (hexagonal architecture with adapters/api, domain, auth_core, services). Frontend consumes REST API at `/api/v1/*` endpoints.

## Phase 0: Outline & Research

**Status**: All technical decisions resolved via spec clarification session (Q1-Q5). No NEEDS CLARIFICATION markers remain.

### Research Tasks (Pre-Resolved via Clarification)

The following research was completed during the feature specification clarification phase:

1. **React-admin Framework Selection**
   - **Decision**: React-admin v4.16+ with marmelab demo template as reference
   - **Rationale**: Production-proven admin framework with built-in CRUD, authentication, and data provider patterns. Significantly reduces development time vs custom implementation.
   - **Alternatives Considered**: Refine (more modern but less mature), AdminJS (Node-centric), custom React+Tanstack setup (higher complexity, more maintenance)
   - **Reference**: <https://github.com/marmelab/react-admin/tree/master/examples/demo>

2. **Authentication Strategy**
   - **Decision**: Hybrid JWT (localStorage access token) + HttpOnly refresh token (secure cookie)
   - **Rationale**: Balances security (XSS protection for refresh token) with usability (no auth server for every request). Supports iframe embedding with `SameSite=None; Secure`. Token rotation prevents replay attacks.
   - **Alternatives Considered**: Session-only (requires backend state, complex in distributed systems), Access token only (no refresh = poor UX), Full OAuth2 flow (overkill for admin interface)

3. **Deployment Architecture**
   - **Decision**: Separate `githubspeckit-frontend` repository with flexible build modes
   - **Rationale**: Independent development pace, third-party extensibility, CI/CD isolation. Production can choose monorepo build (backend serves static) or distributed (CDN + API cluster) based on scale.
   - **Alternatives Considered**: Monorepo only (tight coupling, harder for external contributors), Backend serves JSX (requires Node runtime in backend container)

4. **RBAC UI Implementation**
   - **Decision**: Role-based resource configuration with screen-level permissions (disallowed/readonly/full_crud)
   - **Rationale**: Declarative permissions in resource definitions (DRY). Backend enforces (defense-in-depth). Clear separation of superadmin (cross-tenant) vs tenant_admin (single tenant) vs standard (limited).
   - **Alternatives Considered**: Inline role checks in components (brittle, hard to test), Policy-based UI (too complex for admin interface), Backend-driven UI config (high latency, cache complexity)

5. **Multi-Tenant Context Management**
   - **Decision**: Superadmin-only tenant dropdown + explicit `?tenant_id=` in all API calls
   - **Rationale**: Matches backend test patterns (`test_tenant_isolation.py`). Prevents accidental cross-tenant data access. Non-superadmin calls auto-use JWT tenant_id claim (no switcher visible).
   - **Alternatives Considered**: Implicit tenant context (hidden state = security risk), Subdomain per tenant (requires wildcard SSL, DNS complexity), Separate app per tenant (operational overhead)

### Additional Research Needed (Phase 0 Execution)

Document best practices and implementation patterns:

1. **React-admin AuthProvider Contract**: Review official docs for `login()`, `logout()`, `checkAuth()`, `checkError()`, `getPermissions()`, `getIdentity()` methods. Plan token refresh in `checkError()` on 401 responses.

2. **React-admin DataProvider with Tenant Injection**: Research dataProvider middleware/wrapper pattern to inject `?tenant_id=` query param in all requests. Review `react-admin` source for query parameter handling.

3. **MSW (Mock Service Worker) Setup**: Best practices for mocking REST API in tests and local development. Research MSW v2 syntax for handling multipart/form-data, error scenarios, and request inspection.

4. **Vite Environment Variable Handling**: Confirm `VITE_` prefix convention, `import.meta.env` usage, and build-time vs runtime config strategies. Research `.env.*` file precedence.

5. **React Error Boundary Patterns**: Best practices for component-level and global error boundaries. Research integration with error tracking services (Sentry pattern, generic interface).

6. **Accessibility (WCAG 2.1 Level AA)**: React-admin accessibility features. Research keyboard navigation, ARIA labels, focus management, screen reader compatibility.

7. **Responsive Design for Tablets**: Research react-admin responsive patterns for tablet landscape mode. Material-UI breakpoints (xs/sm/md/lg/xl), CSS Grid/Flexbox for fluid layouts, touch event handling (React onTouchStart/End), minimum touch target sizes (44px per Apple HIG, 48dp per Material Design). React-admin `useMediaQuery()` hook for conditional rendering. Viewport meta tag configuration for proper scaling on tablets.

**Output**: `research.md` documenting decisions and implementation patterns (generated in Phase 0 execution)

## Phase 1: Design & Contracts

Prerequisites: research.md complete

### 1. Frontend Data Model (`data-model.md`)

Extract TypeScript interfaces from backend API contracts (aligned with backend spec.md entities):

**Core Entities** (matching backend domain models):

- **User**: `{ user_id: string, tenant_id: string, email: string, roles: string[], status: 'invited'|'active'|'disabled', created_at: string, updated_at: string }`
- **Tenant**: `{ tenant_id: string, name: string, status: 'active'|'disabled', config_version: number, created_at: string, updated_at: string }`
- **FeatureFlag**: `{ flag_id: string, tenant_id: string, name: string, flag_type: 'boolean'|'string'|'number'|'json', status: 'enabled'|'disabled', values: any, created_at: string, updated_at: string }`
- **Policy**: `{ policy_id: string, tenant_id: string, resource_type: string, action: string, effect: 'ALLOW'|'DENY'|'ABSTAIN', conditions: object, created_at: string, updated_at: string }`
- **Invitation**: `{ invitation_id: string, tenant_id: string, email: string, roles: string[], status: 'pending'|'accepted'|'expired'|'revoked', expires_at: string, created_at: string }`
- **AuditEvent**: `{ event_id: string, tenant_id: string, actor_id: string, action: string, resource_type: string, resource_id: string, timestamp: string, metadata: object }`

**Auth Types**:

- **LoginRequest**: `{ email: string, password: string }`
- **LoginResponse**: `{ access_token: string, token_type: 'Bearer', expires_in: number, user: User }`
- **RefreshResponse**: `{ access_token: string, expires_in: number }`

**Permission Configuration**:

- **ResourcePermission**: `{ resource: string, action: 'list'|'create'|'edit'|'show'|'delete', permission: 'allowed'|'disallowed'|'readonly' }`
- **RolePermissions**: `{ role: string, permissions: ResourcePermission[] }`

### 2. API Client Contracts (`/contracts/`)

Generate TypeScript API client stubs and MSW mock handlers:

**Endpoints to Mock** (from backend spec FR-001 to FR-060):

- **Auth**: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`
- **Users**: `GET /api/v1/users`, `POST /api/v1/users`, `GET /api/v1/users/:id`, `PUT /api/v1/users/:id`, `DELETE /api/v1/users/:id`, `GET /api/v1/users/me`
- **Tenants**: `GET /api/v1/tenants`, `POST /api/v1/tenants`, `GET /api/v1/tenants/:id`, `PUT /api/v1/tenants/:id`, `DELETE /api/v1/tenants/:id`, `POST /api/v1/tenants/:id/restore`
- **Feature Flags**: `GET /api/v1/feature-flags`, `POST /api/v1/feature-flags`, `GET /api/v1/feature-flags/:id`, `PUT /api/v1/feature-flags/:id`, `DELETE /api/v1/feature-flags/:id`
- **Policies**: `GET /api/v1/policies`, `POST /api/v1/policies`, `GET /api/v1/policies/:id`, `PUT /api/v1/policies/:id`, `DELETE /api/v1/policies/:id`
- **Invitations**: `GET /api/v1/invitations`, `POST /api/v1/invitations`, `GET /api/v1/invitations/:id`, `POST /api/v1/invitations/:id/revoke`
- **Audit Events**: `GET /api/v1/audit/events` (read-only, with filters: tenant_id, actor_id, action, date range)

**Contract Files** (in `specs/002-react-admin-frontend/contracts/`):

- `api-types.ts`: All TypeScript interfaces
- `msw-handlers.ts`: MSW request handlers for all endpoints (happy path + error scenarios)
- `api-client.ts`: Axios wrapper with interceptors (auth token injection, tenant_id injection, error handling, token refresh)

### 3. Contract Tests (Failing First)

Generate test files in `tests/` validating API contracts:

**Test Files**:

- `tests/components/authProvider.test.ts`: Test login, logout, checkAuth, checkError (401 → refresh), getPermissions
- `tests/components/dataProvider.test.ts`: Test getList, getOne, create, update, delete for each resource (verify tenant_id injection)
- `tests/integration/auth.test.ts`: Full auth flow (login → access protected resource → token expires → refresh → continue)
- `tests/integration/rbac.test.ts`: Verify resource visibility based on role (superadmin sees all, tenant_admin limited, standard restricted)
- `tests/integration/tenantSwitching.test.ts`: Superadmin switches tenant → verify API calls include new tenant_id

**Test Assertions** (must fail before implementation):

- API calls include correct headers (`Authorization: Bearer {token}`)
- API calls include `?tenant_id={id}` query parameter (except superadmin cross-tenant operations)
- 401 responses trigger token refresh attempt
- 403 responses show user-friendly error (not React stack trace)
- Token expiration doesn't log user out (silent refresh succeeds)

### 4. User Journey Quickstart (`quickstart.md`)

Extract test scenarios from spec.md Acceptance Scenarios:

**Scenario 1: Superadmin Login & Tenant Switching**

1. Navigate to `http://localhost:5173`
2. Login with `infysightsa@infysight.com` / `infysightsa123`
3. Verify dashboard loads with tenant dropdown visible in header
4. Select "Acme Corp" tenant from dropdown
5. Navigate to Users → Create User
6. Verify API request includes `?tenant_id=acme-corp-id`
7. Submit form → User created in Acme Corp tenant

**Scenario 2: Tenant Admin User Management**

1. Login with `infysightadmin@infysight.com` / `infysightadmin123`
2. Verify dashboard loads WITHOUT tenant dropdown (tenant_id fixed to InfySight)
3. Navigate to Users → Create User
4. Verify tenant_id field is read-only (set to InfySight tenant)
5. Submit form with email, roles → User created successfully
6. Navigate to Tenants menu → Verify menu item is hidden (403 forbidden)

**Scenario 3: Standard User Limited Access**

1. Login with `infysightuser@infysight.com` / `infysightuser123`
2. Verify only "Profile" and permitted resources visible in menu
3. Navigate to Profile → Verify user details displayed (GET /api/v1/users/me)
4. Attempt to navigate to `/users` (if permission = disallowed) → Redirect to dashboard or 403 page
5. Navigate to Feature Flags (if permission = readonly) → Verify no "Create" button, Edit/Delete buttons hidden

**Scenario 4: Token Refresh Transparency**

1. Login with any user
2. Wait for access token expiration (mocked to 2 minutes in dev)
3. Perform API action (e.g., navigate to Users list)
4. Verify: No login redirect, API call succeeds, console shows token refresh event

**Scenario 5: Logout & Session Cleanup**

1. Login with any user
2. Click Logout button
3. Verify: Redirect to login page, localStorage cleared, refresh cookie invalidated (backend call to /logout)
4. Attempt to navigate to `/users` → Redirect to login (checkAuth fails)

**Scenario 6: Tablet Responsive Layout**

1. Open application on iPad (Safari) or Android tablet (Chrome) in landscape mode (1024x768+)
2. Login with any user
3. Navigate to Users list
4. Verify: SimpleList rendering (not Datagrid), touch-friendly spacing, no horizontal scroll
5. Verify all buttons/interactive elements are minimum 44x44px (use browser dev tools to measure)
6. Tap "Create User" button → Form opens
7. Verify: Form fields stack vertically or in responsive grid, touch keyboard appears correctly
8. Switch to desktop browser (>1280px width)
9. Verify: Datagrid rendering with all columns, multi-column form layout

### 5. Update Agent Context

Run: `.specify/scripts/bash/update-agent-context.sh copilot`

**Expected Updates** (incremental, preserving existing backend context):

- Add React-admin, TypeScript, Vite to tech stack section
- Add recent changes: "Created separate frontend repository plan with hybrid JWT auth"
- Update project structure: Note frontend in separate repo at `githubspeckit-frontend/`
- Keep backend context intact (hexagonal architecture, FastAPI, SQLAlchemy, etc.)

**Output**: Updated `.github/copilot-instructions.md` with frontend context (keep <150 lines)

### Phase 1 Deliverables

- ✅ `data-model.md`: TypeScript interfaces for all entities + auth types + permission config
- ✅ `contracts/api-types.ts`: Type definitions
- ✅ `contracts/msw-handlers.ts`: MSW mock handlers for all 22 endpoints
- ✅ `contracts/api-client.ts`: Axios wrapper with interceptors
- ✅ Failing contract tests in `tests/components/` and `tests/integration/`
- ✅ `quickstart.md`: 5 user journey scenarios with step-by-step instructions
- ✅ Updated `.github/copilot-instructions.md` with frontend context

## Phase 2: Task Planning Approach

**Description**: This section describes what the /tasks command will do - DO NOT execute during /plan.

### Task Generation Strategy

Load `.specify/templates/tasks-template.md` as base and generate tasks from Phase 1 artifacts:

**Lane A: Project Scaffolding** (Foundation)

1. Initialize `githubspeckit-frontend` repository with Vite + React + TypeScript template
2. Install dependencies (react-admin, @tanstack/react-query, vitest, MSW, etc.)
3. Configure TypeScript strict mode + ESLint + Prettier
4. Setup MSW for API mocking (browser + Node for tests)
5. Create `.env.example` with all `VITE_` variables documented

**Lane B: Type Definitions & Contracts** (TDD Foundation) [P with Lane A]

6. [T] Write failing type tests for all entities (User, Tenant, FeatureFlag, Policy, Invitation, AuditEvent)
7. Implement TypeScript interfaces in `src/types/*.ts` from data-model.md
8. [T] Write failing MSW handler tests (verify mock responses match schemas)
9. Implement MSW handlers in `tests/mocks/handlers.ts` for all 22 endpoints

**Lane C: Authentication Provider** (Critical Path)

10. [T] Write failing authProvider tests (login, logout, checkAuth, checkError, getPermissions, getIdentity)
11. Implement `src/providers/authProvider.ts` with hybrid JWT strategy
12. [T] Write failing token refresh tests (401 → refresh → retry)
13. Implement token refresh logic in `src/utils/api.ts` axios interceptor
14. [T] Write failing integration test: Login → Access protected resource → Token expires → Refresh → Continue

**Lane D: Data Provider with Tenant Injection** (Critical Path)

15. [T] Write failing dataProvider tests (getList, getOne, create, update, delete) with tenant_id assertion
16. Implement `src/providers/dataProvider.ts` wrapping react-admin simpleRestProvider
17. Implement tenant context injection middleware (append `?tenant_id=` to requests)
18. [T] Write failing test: Non-superadmin calls auto-inject JWT tenant_id, Superadmin calls use context tenant_id

**Lane E: Tenant Context & Switcher** (Superadmin Feature) [P with Lane D after step 17]

19. [T] Write failing TenantContext tests (getCurrentTenant, setCurrentTenant, getTenantList)
20. Implement `src/contexts/TenantContext.tsx` React Context Provider
21. [T] Write failing TenantSwitcher component tests (dropdown renders, onChange updates context)
22. Implement `src/components/TenantSwitcher/index.tsx` component
23. [T] Write failing integration test: Superadmin switches tenant → API calls include new tenant_id

**Lane F: Resource Components** (CRUD UIs) [P after Lanes C, D complete]

24. [T] Write failing User resource tests (list, create, edit, show components render)
25. Implement `src/resources/users/` components (UserList, UserCreate, UserEdit, UserShow)
26. [T] Write failing Tenant resource tests
27. Implement `src/resources/tenants/` components
28. [T] Write failing FeatureFlag resource tests
29. Implement `src/resources/featureFlags/` components
30. [T] Write failing Policy resource tests
31. Implement `src/resources/policies/` components
32. [T] Write failing Invitation resource tests
33. Implement `src/resources/invitations/` components
34. [T] Write failing AuditEvent resource tests
35. Implement `src/resources/auditEvents/` components (read-only with filters)

**Lane G: RBAC & Permissions** (Security Layer) [P with Lane F]

36. [T] Write failing permission check tests (role → resource visibility mapping)
37. Implement `src/utils/permissions.ts` permission configuration and check helpers
38. [T] Write failing integration test: Superadmin sees all menus, Tenant_admin limited, Standard restricted
39. Implement role-based menu filtering in `src/App.tsx` (react-admin resource visibility)
40. [T] Write failing test: Standard user with readonly permission sees no Create/Edit/Delete buttons
41. Implement permission-based button visibility in resource components

**Lane H: Layout & Error Handling** [P with Lane G]

42. Implement custom Layout with TenantSwitcher (superadmin only)
43. Implement React Error Boundary components (component-level + global)
44. Implement custom error pages (403 Forbidden, 404 Not Found, 500 Internal Server Error)
45. [T] Write failing tests for error scenarios (API 500 → Error boundary catches → User-friendly message)

**Lane H2: Responsive Design for Tablet Support** [P with Lane H]

46. Configure Material-UI theme with responsive breakpoints and touch-friendly component defaults (44px min)
47. [T] Write failing responsive layout tests (useMediaQuery returns tablet breakpoint → SimpleList renders, not Datagrid)
48. Implement responsive UserList component (Datagrid on desktop, SimpleList on tablet)
49. Implement responsive form layouts with Grid (full width on tablet, multi-column on desktop)
50. Implement responsive TenantSwitcher (adapts width based on viewport)
51. [T] Write failing tests: Touch target sizes meet 44px minimum on all interactive elements
52. Add viewport meta tag with appropriate scaling settings for tablets
53. Test on real tablet devices (iPad Safari, Android Chrome) and document results

**Lane I: Integration Tests & Quickstart Validation**

54. [T] Write failing integration test for Scenario 1 (Superadmin Login & Tenant Switching) from quickstart.md
55. [T] Write failing integration test for Scenario 2 (Tenant Admin User Management)
56. [T] Write failing integration test for Scenario 3 (Standard User Limited Access)
57. [T] Write failing integration test for Scenario 4 (Token Refresh Transparency)
58. [T] Write failing integration test for Scenario 5 (Logout & Session Cleanup)
59. [T] Write failing integration test for Scenario 6 (Tablet Responsive Layout)
60. Execute quickstart.md scenarios manually in dev environment → Document results

**Lane J: Build & Deployment Configuration**

61. Configure Vite build for production (minification, code splitting, asset hashing)
62. Create `DEPLOY_MODE` environment variable handling (separate vs monorepo build outputs)
63. Document deployment strategies in README.md (separate repo, monorepo, CDN)
64. Setup CI/CD pipeline (lint → typecheck → test → build → bundle size report → responsive testing)

### Ordering Strategy

- **TDD Strict**: All tests marked [T] before implementation
- **Dependency Order**: Lanes A, B first (foundation); C, D before E, F (auth/data before UI); G parallel with F (RBAC alongside resources); H, I after core features
- **Parallel Execution**: Mark [P] for tasks in different lanes that don't share files
- **Critical Path**: Lanes C (auth) + D (data) are blockers for all resource work

### Estimated Output

**Total Tasks**: 60-65 numbered, ordered tasks in tasks.md (includes responsive design lane)  
**Estimated Effort**: 70-90 hours (3-4 weeks for single developer, 1.5 weeks for team of 3)  
**Risk Areas**: Token refresh edge cases (401 loops), RBAC permission mapping complexity, MSW handler maintenance burden, responsive layout testing on multiple tablet devices

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

Scope: These phases are beyond the scope of the /plan command.

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

**Status**: No constitutional violations. All complexity justified below.

| Decision | Justification | Simpler Alternative Rejected Because |
|----------|---------------|-------------------------------------|
| Separate Frontend Repository | Independent development velocity for frontend; enables third-party extensions without backend coupling; CI/CD isolation for faster iteration | Monorepo only: Would couple frontend/backend release cycles; makes third-party frontend customization harder; requires backend team approval for frontend changes |
| React-admin Framework | Proven admin framework with 20k+ GitHub stars; reduces 60-80% of boilerplate (auth, data fetching, CRUD UIs); active maintenance + community support | Custom React + Tanstack: Would require 3-4 weeks additional dev time for equivalent features; ongoing maintenance burden; no reference implementations for complex patterns |
| Hybrid JWT + HttpOnly Cookie Auth | Security best practice per OWASP; balances XSS protection (refresh token) with usability (no auth server for every request); iframe embedding compatible | Session-only: Requires backend stateful session store, complex in distributed systems, doesn't work in iframe contexts. Access token only: Poor UX (re-login every 15 min), higher security risk if XSS compromises long-lived token |
| TypeScript Strict Mode | Catches 15-20% of runtime errors at compile time (based on industry studies); improves refactoring confidence; enables better IDE autocomplete | JavaScript: Would require runtime validation for all API responses, higher test burden to catch type errors, harder for new contributors to understand data shapes |
| MSW (Mock Service Worker) | Enables frontend development without backend running; identical mocks in browser (dev) and Node (tests); no network stubbing fragility | Backend dev server required: Slows frontend iteration, creates backend dependency for frontend PRs. HTTP library mocking (e.g., axios-mock-adapter): Different behavior in dev vs tests, harder to maintain |

**Complexity Budget Assessment**:

- **Duplication**: Target <3%. Shared react-admin patterns (list/edit/create) use framework conventions, not copy-paste.
- **Cyclomatic Complexity**: Target avg B, max C per function. Auth/data providers are highest risk areas.
- **Bundle Size**: Target <500KB gzipped. Code splitting by resource (lazy loading) if exceeded.
- **Test Maintenance**: ~40 tests initially. MSW handlers must stay in sync with backend OpenAPI spec (validation in CI).

**Risk Mitigation**:

- **Risk**: MSW handlers drift from actual backend API → Integration failures in production
  - **Mitigation**: Contract tests validate MSW responses match TypeScript types. CI runs frontend tests against real backend (smoke test suite).
- **Risk**: Token refresh logic creates 401 loops (infinite retry)
  - **Mitigation**: Refresh attempt counter with max 1 retry. Failing tests cover edge cases (refresh endpoint returns 401, refresh token expired).
- **Risk**: RBAC permission configuration becomes unmaintainable (100+ rules)
  - **Mitigation**: Start with role-based (3 roles, 6 resources = 18 base rules). Screen-level granularity only if needed (document justification).

## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [x] Phase 0: Research complete (/plan command) ✅ **DONE** (2025-10-12) - research.md generated
- [ ] Phase 1: Design complete (/plan command) - Next: data-model.md, contracts/, tests, quickstart.md
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅ **DONE** - Described above (50-55 tasks in 10 lanes)
- [ ] Phase 3: Tasks generated (/tasks command) - Not yet executed
- [ ] Phase 4: Implementation complete - Pending
- [ ] Phase 5: Validation passed - Pending

**Gate Status**:

- [x] Initial Constitution Check: PASS (2025-10-12) - All 14 principles evaluated, no violations
- [ ] Post-Design Constitution Check: PASS - Will re-evaluate after Phase 1 artifacts generated
- [x] All NEEDS CLARIFICATION resolved - Spec clarification session completed (Q1-Q5), no ambiguities remain
- [x] Complexity deviations documented - See Complexity Tracking table above

**Next Steps**:

1. Execute Phase 1 artifact generation (data-model.md, contracts/, failing tests, quickstart.md)
2. Re-run Constitution Check on generated artifacts
3. If PASS: Proceed to `/tasks` command (Phase 2 execution)
4. If violations: Refactor design, regenerate artifacts, recheck

---
*Based on Constitution v1.5.1 - See `.specify/memory/constitution.md`*
