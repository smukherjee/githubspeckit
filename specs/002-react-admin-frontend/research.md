# Research & Technical Decisions

**Feature**: React-Admin Frontend for Multi-Tenant Backend  
**Date**: 2025-10-12  
**Status**: Complete (pre-resolved via specification clarification)

## Overview

All major technical decisions were resolved during the feature specification clarification phase (Q1-Q5). This document consolidates those decisions with implementation guidance and reference materials.

## 1. Frontend Framework Selection

### Decision

**React-admin v4.16+** with marmelab demo template as reference implementation.

### Rationale

- **Production-Proven**: 20,000+ GitHub stars, used by enterprise companies, 8+ years of active development
- **Velocity**: Reduces 60-80% of admin interface boilerplate (authentication, data fetching, CRUD scaffolding, form handling)
- **Conventions**: Built-in patterns for authProvider, dataProvider, resource definitions eliminate architectural decisions
- **Ecosystem**: Compatible with React 18, Tanstack Query (React Query), Material-UI, react-hook-form
- **Extensibility**: Customizable components, theming, hooks for advanced use cases
- **Documentation**: Comprehensive docs + demo app with real-world patterns

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Refine** | Modern architecture, better TypeScript support, headless UI flexibility | Smaller community (5k stars), less mature (2021), fewer production references | Less proven at scale; risk of breaking changes; community support concerns |
| **AdminJS** | Node.js-centric, auto-generates admin from ORM models | Backend-coupled (requires Node.js backend), limited frontend flexibility, smaller ecosystem | Backend already exists (FastAPI); need frontend flexibility for custom RBAC |
| **Custom React + Tanstack** | Full control, minimal dependencies, modern stack | 3-4 weeks additional dev time, ongoing maintenance burden, no reference patterns | Time-to-market priority; constitutional principle favors simpler approach (avoid NIH) |
| **Retool** | Low-code, rapid prototyping | SaaS lock-in, limited git-based workflow, cost per user, embed limitations | Must be self-hosted, git-tracked, open-source extensible per requirements |

### Implementation Guidance

**Reference Repository**: <https://github.com/marmelab/react-admin/tree/master/examples/demo>

**Key Patterns to Adopt**:

- `<Admin>` component as application root with `authProvider`, `dataProvider`, `i18nProvider`
- Resource definitions with list/create/edit/show components
- Custom layouts for tenant switcher (superadmin)
- Permission-based menu filtering via `getPermissions()` return value
- Optimistic rendering for better UX (react-admin default behavior)

**Architectural Constraints**:

- Use react-admin hooks (`useDataProvider`, `usePermissions`, `useNotify`) instead of direct API calls
- Follow react-admin conventions for resource naming (plural, lowercase)
- Leverage react-admin field components (`<TextField>`, `<DateField>`, `<ChipField>`) for consistency

## 2. Authentication Strategy

### Decision

**Hybrid JWT + HttpOnly Refresh Token**

- **Access Token**: Short-lived (15 minutes), stored in localStorage, sent in `Authorization: Bearer {token}` header
- **Refresh Token**: Long-lived (7 days), stored as HttpOnly, Secure, SameSite=None cookie, sent automatically by browser
- **Token Rotation**: On refresh, old refresh token invalidated, new one issued (prevents replay attacks)

### Rationale

- **XSS Protection**: Refresh token inaccessible to JavaScript (HttpOnly cookie); even if XSS compromises access token, attacker cannot obtain refresh token for long-term access
- **CSRF Mitigation**: Short-lived access token minimizes attack window; backend validates token signature
- **Usability**: No re-login every 15 minutes (transparent refresh); better UX than session-only or access-only approaches
- **Iframe Compatibility**: `SameSite=None; Secure` cookies work in cross-origin iframe contexts (Apache Superset, Power BI embed requirement)
- **Scalability**: Stateless access token; backend doesn't need to store session state (aligns with constitutional Principle V distributed systems)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Session-Only (Cookie)** | Simple server-side control, immediate revocation | Requires stateful session store (Redis/DB), complex in distributed systems, CORS challenges | Backend is stateless (constitutional Principle IV); session store adds operational complexity |
| **Access Token Only (localStorage)** | Simple client-side, no refresh complexity | Poor UX (re-login every 15 min), higher security risk if XSS exploits long-lived token | Unacceptable UX; violates usability requirements (NFR-003) |
| **Full OAuth2/OIDC Flow** | Industry standard, delegation support, SSO-ready | Overkill for admin interface, requires external IdP, complex callback flow | Not needed for internal admin users; future extension point if SSO required |
| **Refresh Token in localStorage** | Simpler client-side storage | XSS vulnerability exposes both tokens, violates OWASP guidelines | Security requirement (Constraint: MUST NOT expose tokens to XSS) explicitly prohibits |

### Implementation Guidance

**AuthProvider Implementation**:

```typescript
// src/providers/authProvider.ts
export const authProvider = {
  login: async ({ email, password }) => {
    const response = await api.post('/api/v1/auth/login', { email, password });
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    // Refresh token set as HttpOnly cookie by backend (Set-Cookie header)
    return Promise.resolve();
  },
  
  checkAuth: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return Promise.reject();
    // Optionally validate token expiration (JWT decode exp claim)
    return Promise.resolve();
  },
  
  checkError: async (error) => {
    if (error.status === 401) {
      // Attempt token refresh
      try {
        const response = await api.post('/api/v1/auth/refresh'); // Cookie sent automatically
        localStorage.setItem('access_token', response.data.access_token);
        return Promise.resolve(); // Auth still valid after refresh
      } catch {
        localStorage.removeItem('access_token');
        return Promise.reject(); // Refresh failed, redirect to login
      }
    }
    return Promise.resolve(); // Other errors don't affect auth
  },
  
  logout: async () => {
    await api.post('/api/v1/auth/logout'); // Invalidate refresh token on backend
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    return Promise.resolve();
  },
  
  getPermissions: async () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    return Promise.resolve(user.roles); // ['superadmin'] or ['tenant_admin'] or ['standard']
  },
  
  getIdentity: async () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    return Promise.resolve({
      id: user.user_id,
      fullName: user.email,
      avatar: undefined
    });
  }
};
```

**Axios Interceptor for Token Injection**:

```typescript
// src/utils/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true // Send cookies (refresh token)
});

// Request interceptor: Inject access token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle token refresh on 401
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue request until refresh completes
        return new Promise((resolve) => {
          refreshSubscribers.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      try {
        const response = await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken = response.data.access_token;
        localStorage.setItem('access_token', newToken);
        
        // Notify queued requests
        refreshSubscribers.forEach((callback) => callback(newToken));
        refreshSubscribers = [];
        
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

**Security Considerations**:

- **XSS Prevention**: React auto-escapes by default; avoid `dangerouslySetInnerHTML`; implement Content Security Policy (CSP) headers
- **Token Storage**: Never store refresh token in localStorage/sessionStorage; only HttpOnly cookie
- **Token Expiration**: Access token exp claim validated on backend (not frontend); frontend only checks presence
- **Logout**: Always call `/logout` endpoint to invalidate refresh token server-side (prevent reuse)

## 3. Deployment Architecture

### Decision

**Separate `githubspeckit-frontend` repository** with flexible production build modes:

- **Development**: Independent frontend repo for fast iteration
- **Production Low Volume**: Monorepo build (backend serves static assets from `/static`)
- **Production High Volume**: Distributed deployment (frontend CDN/container + backend API cluster)

### Rationale

- **Independent Velocity**: Frontend PRs don't require backend review; faster iteration cycles
- **Third-Party Extensions**: External contributors can fork frontend repo without backend access; aligns with open-source friendly architecture
- **CI/CD Isolation**: Frontend builds/tests run independently; no waiting for backend pipeline
- **Deployment Flexibility**: Single source can deploy multiple ways based on scale/cost requirements
- **Team Structure**: Enables separate frontend/backend teams if needed (common in larger orgs)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Monorepo Only** | Simpler versioning, atomic commits across frontend/backend | Tight coupling, frontend changes require backend CI approval, harder for external contributors | Limits third-party extensibility (constitutional Principle VIII developer experience) |
| **Backend Serves JSX (SSR)** | Unified runtime, better SEO (not needed for admin), simpler deployment | Requires Node.js in backend container (currently Python-only), complicates backend architecture | Backend is Python/FastAPI; adding Node.js violates simplicity (constitutional Principle IX KISS) |
| **Frontend-Only (No Monorepo Option)** | Maximum independence | Forces separate deployment even for small/prototype setups, operational overhead for low-volume use cases | Violates developer experience requirement (Principle VIII 5-minute bootstrap for new contributors) |

### Implementation Guidance

**Environment Variable Configuration**:

```bash
# .env.development (separate repo dev mode)
VITE_API_BASE_URL=http://localhost:8000
VITE_DEPLOY_MODE=separate

# .env.production (monorepo build mode)
VITE_API_BASE_URL=/api  # Relative URL (same domain)
VITE_DEPLOY_MODE=monorepo

# .env.production (distributed mode)
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_DEPLOY_MODE=distributed
```

**Build Output Configuration** (`vite.config.ts`):

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: process.env.VITE_DEPLOY_MODE === 'monorepo' 
      ? '../backend/static'  // Output to backend static folder
      : 'dist',              // Separate deployment
    emptyOutDir: true,
    sourcemap: process.env.NODE_ENV !== 'production',
  },
  server: {
    proxy: process.env.VITE_DEPLOY_MODE === 'separate' 
      ? {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          }
        }
      : undefined
  }
});
```

**Backend Static File Serving** (monorepo mode only):

```python
# backend/src/main.py (FastAPI app)
from fastapi.staticfiles import StaticFiles
import os

DEPLOY_MODE = os.getenv("DEPLOY_MODE", "backend-only")

if DEPLOY_MODE == "monorepo":
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

**CI/CD Strategy**:

- **Development**: `npm run dev` (Vite dev server with HMR + proxy to backend)
- **Production Monorepo**: `npm run build` → outputs to `../backend/static` → backend serves
- **Production Distributed**: `npm run build` → upload `dist/` to CDN/S3 or deploy to separate container

## 4. RBAC UI Implementation

### Decision

**Role-based resource configuration with screen-level permissions** (disallowed/readonly/full_crud)

- **Superadmin**: Full CRUD across all resources + tenant dropdown switcher
- **Tenant_admin**: Full CRUD within own tenant (no tenant switcher)
- **Standard**: Screen-level permissions per resource (disallowed = hidden, readonly = no edit buttons, full_crud = all operations)

### Rationale

- **Declarative Configuration**: Permissions defined in resource configuration objects (DRY); not scattered across component code
- **Defense-in-Depth**: Backend enforces authorization on every API call; frontend permissions only control UI visibility
- **Clear Semantics**: Three permission levels cover 90% of admin use cases without complex policy language
- **Testability**: Permission checks isolated in `src/utils/permissions.ts`; easy to test without rendering components
- **Extensibility**: Adding new resources requires one permission entry per role (3 entries per resource = 18 total for 6 resources)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Inline Role Checks (`if (user.role === 'admin')`)** | Simple, no abstraction | Brittle, hard to test, scattered logic, violates DRY | Fails constitutional Principle IX code quality (no inline branching) |
| **Policy-Based UI (evaluate conditions on every render)** | Fine-grained control, attribute-based access | Complex, performance overhead, overkill for admin interface | Violates YAGNI (Principle IX); admin interface doesn't need attribute-based policies |
| **Backend-Driven UI Config (API returns permission JSON)** | Single source of truth | High latency (extra API call), caching complexity, harder to debug | Poor UX (loading spinners everywhere); frontend should render immediately with JWT roles |

### Implementation Guidance

**Permission Configuration** (`src/utils/permissions.ts`):

```typescript
export type Permission = 'disallowed' | 'readonly' | 'full_crud';

export interface ResourcePermissions {
  list: Permission;
  create: Permission;
  edit: Permission;
  show: Permission;
  delete: Permission;
}

// Default permissions by role
export const ROLE_PERMISSIONS: Record<string, Record<string, ResourcePermissions>> = {
  superadmin: {
    users: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    tenants: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    featureFlags: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    policies: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    invitations: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    auditEvents: { list: 'full_crud', create: 'disallowed', edit: 'disallowed', show: 'full_crud', delete: 'disallowed' },
  },
  tenant_admin: {
    users: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    tenants: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
    featureFlags: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    policies: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    invitations: { list: 'full_crud', create: 'full_crud', edit: 'full_crud', show: 'full_crud', delete: 'full_crud' },
    auditEvents: { list: 'readonly', create: 'disallowed', edit: 'disallowed', show: 'readonly', delete: 'disallowed' },
  },
  standard: {
    users: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
    tenants: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
    featureFlags: { list: 'readonly', create: 'disallowed', edit: 'disallowed', show: 'readonly', delete: 'disallowed' },
    policies: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
    invitations: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
    auditEvents: { list: 'disallowed', create: 'disallowed', edit: 'disallowed', show: 'disallowed', delete: 'disallowed' },
  },
};

export function getResourcePermission(
  roles: string[],
  resource: string,
  action: keyof ResourcePermissions
): Permission {
  // Superadmin takes precedence
  if (roles.includes('superadmin')) {
    return ROLE_PERMISSIONS.superadmin[resource]?.[action] || 'disallowed';
  }
  
  // Tenant_admin next
  if (roles.includes('tenant_admin')) {
    return ROLE_PERMISSIONS.tenant_admin[resource]?.[action] || 'disallowed';
  }
  
  // Standard or other roles (most restrictive)
  return ROLE_PERMISSIONS.standard[resource]?.[action] || 'disallowed';
}

export function canAccessResource(roles: string[], resource: string): boolean {
  return getResourcePermission(roles, resource, 'list') !== 'disallowed';
}

export function canCreateResource(roles: string[], resource: string): boolean {
  return getResourcePermission(roles, resource, 'create') === 'full_crud';
}

export function canEditResource(roles: string[], resource: string): boolean {
  return getResourcePermission(roles, resource, 'edit') === 'full_crud';
}

export function canDeleteResource(roles: string[], resource: string): boolean {
  return getResourcePermission(roles, resource, 'delete') === 'full_crud';
}
```

**React-Admin Resource Registration** (`src/App.tsx`):

```typescript
import { Admin, Resource, ListGuesser } from 'react-admin';
import { authProvider } from './providers/authProvider';
import { dataProvider } from './providers/dataProvider';
import { usePermissions } from 'react-admin';
import { canAccessResource } from './utils/permissions';

function App() {
  return (
    <Admin authProvider={authProvider} dataProvider={dataProvider}>
      <CustomResources />
    </Admin>
  );
}

function CustomResources() {
  const { permissions, isLoading } = usePermissions();
  
  if (isLoading) return null;
  
  return (
    <>
      {canAccessResource(permissions, 'users') && (
        <Resource name="users" list={UserList} create={UserCreate} edit={UserEdit} show={UserShow} />
      )}
      {canAccessResource(permissions, 'tenants') && (
        <Resource name="tenants" list={TenantList} create={TenantCreate} edit={TenantEdit} show={TenantShow} />
      )}
      {canAccessResource(permissions, 'featureFlags') && (
        <Resource name="feature-flags" list={FeatureFlagList} /* ... */ />
      )}
      {/* ... other resources */}
    </>
  );
}
```

**Conditional Button Rendering** (in resource components):

```typescript
import { List, Datagrid, TextField, EditButton, DeleteButton } from 'react-admin';
import { usePermissions } from 'react-admin';
import { canEditResource, canDeleteResource } from '../utils/permissions';

export const UserList = () => {
  const { permissions } = usePermissions();
  
  return (
    <List>
      <Datagrid>
        <TextField source="email" />
        <TextField source="status" />
        {canEditResource(permissions, 'users') && <EditButton />}
        {canDeleteResource(permissions, 'users') && <DeleteButton />}
      </Datagrid>
    </List>
  );
};
```

## 5. Multi-Tenant Context Management

### Decision

**Superadmin-only tenant dropdown** in application header + **explicit `?tenant_id=` query parameter** in all API calls

- **Superadmin**: Dropdown to select active tenant context; all API calls include selected tenant_id
- **Non-Superadmin**: JWT tenant_id claim auto-injected; no dropdown visible (tenant fixed)
- **API Pattern**: `GET /api/v1/users?tenant_id=acme-corp-123` (matches backend `test_tenant_isolation.py` pattern)

### Rationale

- **Explicit Scoping**: Every API call has visible tenant_id parameter; no hidden state or implicit context
- **Security**: Non-superadmin users cannot modify tenant_id (enforced by backend validation against JWT claim)
- **Backend Consistency**: Matches existing backend test patterns (see `test_tenant_lifecycle.py` line 273, 211)
- **Auditability**: Tenant context visible in browser DevTools network tab; easy to debug/verify
- **Simplicity**: React Context Provider manages single piece of state (selected tenant); no complex state machine

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Implicit Tenant Context (Hidden State)** | Cleaner API calls (no repetitive query param) | Security risk (accidental cross-tenant access), harder to debug, backend must infer from JWT only | Violates explicit tenant scoping (constitutional Principle III); backend tests already use explicit pattern |
| **Subdomain per Tenant (`acme.yourdomain.com`)** | Clear tenant isolation at URL level, better for white-labeling | Requires wildcard SSL cert, DNS management complexity, backend subdomain routing | Operational overhead too high; not needed for admin interface (different from customer-facing app) |
| **Separate App Instance per Tenant** | Maximum isolation, independent scaling | Operational nightmare (deploy/monitor 100s of instances), version drift, high cost | Violates simplicity (Principle IX); single app with RBAC is sufficient for admin use case |
| **Tenant ID in JWT Only (No Query Param)** | Simpler API calls | Superadmin cannot switch tenants (JWT tenant_id is fixed), backend must extract from token every time | Breaks superadmin cross-tenant management requirement (FR-009) |

### Implementation Guidance

**Tenant Context Provider** (`src/contexts/TenantContext.tsx`):

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';

interface Tenant {
  tenant_id: string;
  name: string;
}

interface TenantContextValue {
  currentTenant: Tenant | null;
  setCurrentTenant: (tenant: Tenant) => void;
  tenantList: Tenant[];
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [tenantList, setTenantList] = useState<Tenant[]>([]);
  
  useEffect(() => {
    // Fetch tenant list on mount (superadmin only)
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.roles?.includes('superadmin')) {
      fetch('/api/v1/tenants', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
        .then((res) => res.json())
        .then((data) => {
          setTenantList(data.tenants || data);
          if (data.tenants?.length > 0) {
            setCurrentTenant(data.tenants[0]); // Default to first tenant
          }
        });
    } else {
      // Non-superadmin: use JWT tenant_id as fixed context
      setCurrentTenant({ tenant_id: user.tenant_id, name: user.tenant_name || 'Your Tenant' });
    }
  }, []);
  
  return (
    <TenantContext.Provider value={{ currentTenant, setCurrentTenant, tenantList }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within TenantProvider');
  }
  return context;
}
```

**Data Provider with Tenant Injection** (`src/providers/dataProvider.ts`):

```typescript
import { fetchUtils, DataProvider } from 'react-admin';
import { stringify } from 'query-string';

const httpClient = (url: string, options: any = {}) => {
  if (!options.headers) {
    options.headers = new Headers({ Accept: 'application/json' });
  }
  const token = localStorage.getItem('access_token');
  if (token) {
    options.headers.set('Authorization', `Bearer ${token}`);
  }
  return fetchUtils.fetchJson(url, options);
};

export const dataProvider = (
  getCurrentTenant: () => { tenant_id: string } | null
): DataProvider => ({
  getList: (resource, params) => {
    const { page, perPage } = params.pagination;
    const { field, order } = params.sort;
    const query = {
      sort: field,
      order: order,
      page: page,
      per_page: perPage,
      ...params.filter,
      tenant_id: getCurrentTenant()?.tenant_id, // Inject tenant_id
    };
    const url = `${apiUrl}/${resource}?${stringify(query)}`;
    return httpClient(url).then(({ json }) => ({
      data: json.data || json,
      total: json.total || json.length,
    }));
  },
  
  getOne: (resource, params) => {
    const query = { tenant_id: getCurrentTenant()?.tenant_id };
    const url = `${apiUrl}/${resource}/${params.id}?${stringify(query)}`;
    return httpClient(url).then(({ json }) => ({ data: json }));
  },
  
  create: (resource, params) => {
    const body = {
      ...params.data,
      tenant_id: getCurrentTenant()?.tenant_id, // Inject into body
    };
    return httpClient(`${apiUrl}/${resource}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }).then(({ json }) => ({ data: json }));
  },
  
  // ... similar for update, delete, etc.
});
```

**Tenant Switcher Component** (`src/components/TenantSwitcher/index.tsx`):

```typescript
import { Select, MenuItem } from '@mui/material';
import { useTenant } from '../../contexts/TenantContext';

export function TenantSwitcher() {
  const { currentTenant, setCurrentTenant, tenantList } = useTenant();
  
  if (tenantList.length === 0) return null; // Non-superadmin
  
  return (
    <Select
      value={currentTenant?.tenant_id || ''}
      onChange={(e) => {
        const tenant = tenantList.find((t) => t.tenant_id === e.target.value);
        if (tenant) setCurrentTenant(tenant);
      }}
      displayEmpty
      sx={{ minWidth: 200, color: 'white' }}
    >
      {tenantList.map((tenant) => (
        <MenuItem key={tenant.tenant_id} value={tenant.tenant_id}>
          {tenant.name}
        </MenuItem>
      ))}
    </Select>
  );
}
```

**Custom Layout Integration** (`src/App.tsx`):

```typescript
import { Layout, AppBar } from 'react-admin';
import { TenantSwitcher } from './components/TenantSwitcher';

const CustomAppBar = () => (
  <AppBar>
    <span style={{ flex: 1 }} />
    <TenantSwitcher />
  </AppBar>
);

const CustomLayout = (props: any) => <Layout {...props} appBar={CustomAppBar} />;

function App() {
  return (
    <TenantProvider>
      <Admin
        authProvider={authProvider}
        dataProvider={dataProvider(() => useTenant().currentTenant)}
        layout={CustomLayout}
      >
        {/* resources */}
      </Admin>
    </TenantProvider>
  );
}
```

## 6. Responsive Design for Tablet Support

### Decision

**Responsive design supporting tablet landscape mode** (iPad 1024x768+, Android 960x600+) with:

- Material-UI responsive breakpoints (xs/sm/md/lg/xl)
- CSS Grid and Flexbox for fluid layouts
- Touch-friendly UI elements (minimum 44px touch targets)
- React-admin responsive patterns and `useMediaQuery()` hook

### Rationale

- **Admin Use Case**: Admins often work from tablets in field operations, warehouses, or mobile contexts
- **Landscape Optimization**: Admin interfaces have horizontal information density (data tables, forms) that fit landscape better than portrait
- **React-admin Native Support**: Framework includes responsive components and hooks out-of-the-box
- **Material-UI Foundation**: Built on Material-UI which has robust responsive grid system
- **Touch Accessibility**: Larger touch targets improve usability and meet WCAG 2.1 AA standards (2.5.5 Target Size)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Desktop Only** | Simpler development, no touch considerations | Excludes tablet users, poor field admin experience | User requirement explicitly asks for tablet support |
| **Mobile-First (Portrait)** | Best practice for public apps, broader device support | Admin interface too cramped on portrait phones, data tables unreadable | Admin interface not suitable for small screens; landscape tablets sufficient |
| **Native App (iOS/Android)** | Best touch experience, native APIs, offline support | Requires separate codebase per platform, no web embed support, higher maintenance | Constitutional Principle IX (KISS): Web app covers 90% use cases without platform-specific complexity |
| **Progressive Web App (PWA)** | Offline support, installable, push notifications | Service worker complexity, limited iOS PWA support, not needed for admin interface | YAGNI (Principle IX): Admin users online by definition; PWA features overkill |

### Implementation Guidance

**Material-UI Breakpoints** (react-admin uses Material-UI v5):

```typescript
// Default Material-UI breakpoints
const breakpoints = {
  xs: 0,      // Phone portrait
  sm: 600,    // Phone landscape
  md: 960,    // Tablet portrait
  lg: 1280,   // Tablet landscape / Desktop
  xl: 1920,   // Large desktop
};

// Tablet landscape targets: md (960-1279px) and lg (1280-1919px)
```

**Responsive Layout Configuration** (`src/App.tsx`):

```typescript
import { Admin, Layout, defaultTheme } from 'react-admin';
import { createTheme } from '@mui/material/styles';

// Custom theme with responsive spacing
const theme = createTheme({
  ...defaultTheme,
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,   // Tablet portrait
      lg: 1280,  // Tablet landscape (target)
      xl: 1920,
    },
  },
  spacing: 8, // 8px base unit; touch targets = 44px = 5.5 * spacing
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 44, // Touch-friendly minimum
          minWidth: 44,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          minHeight: 44,
          minWidth: 44,
        },
      },
    },
  },
});

function App() {
  return (
    <Admin theme={theme} /* ... */>
      {/* resources */}
    </Admin>
  );
}
```

**Responsive Datagrid** (resource list views):

```typescript
import { List, Datagrid, SimpleList, TextField, useMediaQuery } from 'react-admin';
import { useTheme } from '@mui/material/styles';

export const UserList = () => {
  const theme = useTheme();
  const isTablet = useMediaQuery(theme.breakpoints.down('lg')); // <1280px
  
  return (
    <List>
      {isTablet ? (
        // Tablet: Simpler list view with fewer columns
        <SimpleList
          primaryText={(record) => record.email}
          secondaryText={(record) => `${record.roles.join(', ')} - ${record.status}`}
          tertiaryText={(record) => new Date(record.created_at).toLocaleDateString()}
          linkType="show"
        />
      ) : (
        // Desktop: Full datagrid with all columns
        <Datagrid>
          <TextField source="email" />
          <TextField source="status" />
          <TextField source="roles" />
          <DateField source="created_at" />
          <EditButton />
          <DeleteButton />
        </Datagrid>
      )}
    </List>
  );
};
```

**Responsive Forms** (create/edit views):

```typescript
import { SimpleForm, TextInput, SelectInput, required } from 'react-admin';
import { Grid } from '@mui/material';

export const UserCreate = () => (
  <SimpleForm>
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        {/* Full width on tablet, half width on desktop */}
        <TextInput source="email" validate={required()} fullWidth />
      </Grid>
      <Grid item xs={12} md={6}>
        <SelectInput source="status" choices={[...]} fullWidth />
      </Grid>
      <Grid item xs={12}>
        <SelectInput source="roles" choices={[...]} multiple fullWidth />
      </Grid>
    </Grid>
  </SimpleForm>
);
```

**Touch Gesture Support**:

React-admin's Material-UI components support touch events by default:
- **Tap**: Standard button/link clicks
- **Swipe**: List scrolling (native browser behavior)
- **Pinch-to-zoom**: Disabled via viewport meta tag for consistent UI (admin interface doesn't need zoom)

**Viewport Meta Tag** (`public/index.html`):

```html
<meta 
  name="viewport" 
  content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
/>
```

**Responsive Tenant Switcher**:

```typescript
import { Select, MenuItem, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { useTenant } from '../../contexts/TenantContext';

export function TenantSwitcher() {
  const theme = useTheme();
  const isTablet = useMediaQuery(theme.breakpoints.down('lg'));
  const { currentTenant, setCurrentTenant, tenantList } = useTenant();
  
  if (tenantList.length === 0) return null;
  
  return (
    <Select
      value={currentTenant?.tenant_id || ''}
      onChange={(e) => {
        const tenant = tenantList.find((t) => t.tenant_id === e.target.value);
        if (tenant) setCurrentTenant(tenant);
      }}
      displayEmpty
      sx={{ 
        minWidth: isTablet ? 150 : 200,  // Narrower on tablet
        minHeight: 44,                   // Touch-friendly
        color: 'white' 
      }}
    >
      {tenantList.map((tenant) => (
        <MenuItem 
          key={tenant.tenant_id} 
          value={tenant.tenant_id}
          sx={{ minHeight: 44 }}  // Touch-friendly menu items
        >
          {tenant.name}
        </MenuItem>
      ))}
    </Select>
  );
}
```

**Testing Responsive Layouts**:

```typescript
// tests/components/responsive.test.tsx
import { render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useMediaQuery } from '@mui/material';
import { UserList } from '../../resources/users/UserList';

// Mock useMediaQuery for testing
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  useMediaQuery: jest.fn(),
}));

test('UserList renders SimpleList on tablet breakpoint', () => {
  (useMediaQuery as jest.Mock).mockReturnValue(true); // Simulate tablet
  
  render(
    <ThemeProvider theme={createTheme()}>
      <UserList />
    </ThemeProvider>
  );
  
  // Assert SimpleList rendering (specific to tablet view)
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('UserList renders Datagrid on desktop breakpoint', () => {
  (useMediaQuery as jest.Mock).mockReturnValue(false); // Simulate desktop
  
  render(
    <ThemeProvider theme={createTheme()}>
      <UserList />
    </ThemeProvider>
  );
  
  // Assert Datagrid rendering (specific to desktop view)
  expect(screen.getByRole('table')).toBeInTheDocument();
});
```

**CSS Media Queries** (for custom components):

```css
/* src/components/Dashboard/Dashboard.css */
.dashboard-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

/* Tablet landscape: 2 columns */
@media (min-width: 960px) and (max-width: 1279px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: 3+ columns */
@media (min-width: 1280px) {
  .dashboard-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Ensure touch targets meet minimum size */
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

**Performance Considerations**:

- **Lazy Loading**: Use React.lazy() for resource components to reduce initial bundle size on tablet devices
- **Image Optimization**: Serve responsive images via `<picture>` element with srcset for different resolutions
- **Network Detection**: Use `navigator.connection` API to detect slow networks on tablets; show simplified views if needed

### Browser Testing Requirements

- **iPad Safari** (iOS 14+): Primary tablet target
- **Chrome on Android tablets** (Android 10+)
- **Samsung Internet** (Samsung tablets)
- **Edge on Surface tablets** (Windows)

**Responsive Design Checklist**:

- [ ] All buttons/interactive elements minimum 44x44px
- [ ] List views switch to SimpleList on tablet breakpoints
- [ ] Forms use Grid layout with responsive column spans
- [ ] Tenant switcher width adapts to viewport
- [ ] Navigation menu collapsible on smaller tablets
- [ ] No horizontal scrolling required (viewport-width layouts)
- [ ] Tested on real iPad and Android tablet devices

## Summary

All major technical decisions finalized. No NEEDS CLARIFICATION markers remain. Implementation guidance provided for:

1. **React-admin framework** with marmelab demo reference
2. **Hybrid JWT authentication** with axios interceptor for token refresh
3. **Separate frontend repository** with flexible deployment modes
4. **Declarative RBAC permissions** with screen-level granularity
5. **Explicit tenant context** with superadmin switcher + query parameter injection
6. **Responsive design for tablet support** with Material-UI breakpoints, touch-friendly UI, and adaptive layouts

Ready for Phase 1: Design & Contracts (data-model.md, contracts/, failing tests, quickstart.md).
