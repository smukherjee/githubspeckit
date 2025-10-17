# Data Model: Admin API Backend Entities

**Feature**: Admin API Endpoints for Multi-Tenant Backend  
**Date**: 2025-10-17  
**Status**: Phase 1 Design

## Overview

This document defines the backend data models exposed through the admin API endpoints. These models represent domain entities, validation rules, and API contracts for frontend-agnostic consumption by any client framework.

## Core Entities

### 1. User Entity

**Purpose**: Represents system users across all tenants

```typescript
interface User {
  // Core identification
  user_id: string;           // UUID primary key
  tenant_id: string;         // UUID foreign key to Tenant
  email: string;             // Unique within tenant, login identifier
  
  // Authentication & Status
  password_hash?: string;    // Only returned on certain admin operations
  is_disabled: boolean;      // Account activation status
  failed_login_attempts: number;
  last_login_at?: Date;      // ISO 8601 timestamp
  
  // Profile Information
  full_name?: string;        // Display name
  job_title?: string;        // Professional title
  department?: string;       // Organizational unit
  phone?: string;           // Contact information
  timezone?: string;        // IANA timezone identifier (e.g., 'America/New_York')
  language?: string;        // Language preference (ISO 639-1, e.g., 'en', 'es')
  
  // RBAC
  roles: string[];          // ['superadmin'] | ['tenant_admin'] | ['standard']
  
  // Audit fields
  created_at: Date;         // ISO 8601 timestamp
  updated_at: Date;         // ISO 8601 timestamp
  created_by: string;       // UUID of creating user
  updated_by: string;       // UUID of last updating user
}
```

**Validation Rules**:

- `email`: Must be valid email format, unique within tenant
- `roles`: Must be one of: `superadmin`, `tenant_admin`, `standard`
- `timezone`: Must be valid IANA timezone identifier
- `language`: Must be valid ISO 639-1 language code
- `phone`: Optional E.164 format validation

**State Transitions**:

- `is_disabled`: `false` (active) ↔ `true` (disabled)
- `failed_login_attempts`: Increments on failed login, resets on successful login

### 2. Tenant Entity

**Purpose**: Represents organizational tenants in multi-tenant system

```typescript
interface Tenant {
  // Core identification
  tenant_id: string;        // UUID primary key
  name: string;            // Organization name
  
  // Status & Configuration
  is_active: boolean;      // Tenant activation status
  settings?: {             // Tenant-specific configuration
    max_users?: number;    // User limit for this tenant
    features?: string[];   // Enabled features list
    branding?: {
      logo_url?: string;
      primary_color?: string;
      secondary_color?: string;
    };
  };
  
  // Audit fields
  created_at: Date;        // ISO 8601 timestamp
  updated_at: Date;        // ISO 8601 timestamp
  created_by: string;      // UUID of creating user
  updated_by: string;      // UUID of last updating user
}
```

**Validation Rules**:

- `name`: Required, 1-100 characters, unique across system
- `settings.max_users`: Positive integer or null
- `settings.branding.primary_color`: Valid hex color code
- `settings.branding.secondary_color`: Valid hex color code

**State Transitions**:

- `is_active`: `false` (inactive) ↔ `true` (active)

### 3. Policy Entity

**Purpose**: Represents RBAC policies for authorization

```typescript
interface Policy {
  // Core identification
  policy_id: string;       // UUID primary key
  tenant_id: string;       // UUID foreign key to Tenant
  name: string;           // Policy identifier
  
  // Policy Definition
  resource: string;       // Resource type (e.g., 'users', 'tenants', 'policies')
  action: string;         // Action type (e.g., 'create', 'read', 'update', 'delete')
  conditions?: {          // Optional conditions
    resource_owner?: boolean;  // Policy applies only to owned resources
    same_tenant?: boolean;     // Policy applies only within same tenant
    custom_rules?: Record<string, any>; // Additional custom conditions
  };
  
  // Authorization
  effect: 'ALLOW' | 'DENY'; // Policy effect
  roles: string[];         // Applicable roles
  priority: number;        // Policy evaluation priority (higher = first)
  
  // Status
  is_active: boolean;      // Policy activation status
  
  // Audit fields
  created_at: Date;        // ISO 8601 timestamp
  updated_at: Date;        // ISO 8601 timestamp
  created_by: string;      // UUID of creating user
  updated_by: string;      // UUID of last updating user
}
```

**Validation Rules**:

- `name`: Required, unique within tenant
- `resource`: Must be valid resource type from system
- `action`: Must be valid action type (CRUD operations)
- `effect`: Must be 'ALLOW' or 'DENY'
- `roles`: Must contain valid role names
- `priority`: Integer between 0-1000

### 4. Feature Flag Entity

**Purpose**: Represents feature toggles for gradual rollouts

```typescript
interface FeatureFlag {
  // Core identification
  flag_id: string;         // UUID primary key
  tenant_id?: string;      // UUID foreign key to Tenant (null for global flags)
  name: string;           // Feature flag identifier
  
  // Configuration
  is_enabled: boolean;     // Feature activation status
  description?: string;    // Human-readable description
  rollout_percentage?: number; // Gradual rollout percentage (0-100)
  target_users?: string[]; // Specific user IDs for targeted rollout
  
  // Metadata
  created_at: Date;        // ISO 8601 timestamp
  updated_at: Date;        // ISO 8601 timestamp
  created_by: string;      // UUID of creating user
  updated_by: string;      // UUID of last updating user
}
```

**Validation Rules**:

- `name`: Required, unique within tenant scope
- `rollout_percentage`: Integer between 0-100
- `target_users`: Array of valid user UUIDs

### 5. Invitation Entity

**Purpose**: Represents pending user invitations

```typescript
interface Invitation {
  // Core identification
  invitation_id: string;   // UUID primary key
  tenant_id: string;       // UUID foreign key to Tenant
  email: string;          // Invitee email address
  
  // Invitation Details
  roles: string[];        // Roles to assign upon acceptance
  invited_by: string;     // UUID of inviting user
  
  // Status & Expiration
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  expires_at: Date;       // ISO 8601 timestamp
  accepted_at?: Date;     // ISO 8601 timestamp
  accepted_by?: string;   // UUID of user who accepted
  
  // Security
  invitation_token: string; // Secure token for invitation acceptance
  
  // Audit fields
  created_at: Date;        // ISO 8601 timestamp
  updated_at: Date;        // ISO 8601 timestamp
}
```

**Validation Rules**:

- `email`: Must be valid email format
- `status`: Must be one of the defined enum values
- `expires_at`: Must be future date
- `roles`: Must contain valid role names

**State Transitions**:

- `pending` → `accepted` (user accepts invitation)
- `pending` → `expired` (expiration time reached)
- `pending` → `revoked` (admin revokes invitation)

### 6. Audit Event Entity

**Purpose**: Represents system audit trail events

```typescript
interface AuditEvent {
  // Core identification
  event_id: string;        // UUID primary key
  tenant_id?: string;      // UUID foreign key to Tenant (null for system events)
  
  // Event Details
  event_type: string;      // Event classification (e.g., 'user.created', 'policy.updated')
  resource_type: string;   // Type of resource affected
  resource_id: string;     // ID of affected resource
  
  // Actor Information
  actor_id?: string;       // UUID of user who performed action (null for system)
  actor_type: 'user' | 'system'; // Type of actor
  
  // Event Data
  action: string;          // Action performed (create, update, delete, etc.)
  changes?: {              // What changed (for update operations)
    before?: Record<string, any>;
    after?: Record<string, any>;
  };
  metadata?: Record<string, any>; // Additional context
  
  // Request Context
  ip_address?: string;     // Client IP address
  user_agent?: string;     // Client user agent
  session_id?: string;     // Session identifier
  
  // Timestamp
  occurred_at: Date;       // ISO 8601 timestamp when event occurred
}
```

**Validation Rules**:

- `event_type`: Must follow dot notation (e.g., 'resource.action')
- `actor_type`: Must be 'user' or 'system'
- `ip_address`: Must be valid IPv4 or IPv6 address
- `occurred_at`: Must be valid ISO 8601 timestamp

## Frontend-Specific Models

### 7. UI State Models

**Purpose**: Frontend-only models for UI state management

```typescript
// Current user session
interface UserSession {
  user: User;
  tenant: Tenant;
  permissions: string[];
  access_token: string;
  token_expires_at: Date;
  selected_tenant_id?: string; // For superadmin tenant switching
}

// Data provider responses
interface ListResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
  timestamp: Date;
}

// Form state for user creation/editing
interface UserFormData {
  email: string;
  full_name?: string;
  job_title?: string;
  department?: string;
  phone?: string;
  timezone?: string;
  language?: string;
  roles: string[];
  is_disabled: boolean;
  password?: string; // Only for creation
}
```

## Relationships

```text
Tenant 1:many User (tenant_id → tenant_id)
Tenant 1:many Policy (tenant_id → tenant_id)
Tenant 1:many FeatureFlag (tenant_id → tenant_id)
Tenant 1:many Invitation (tenant_id → tenant_id)
Tenant 1:many AuditEvent (tenant_id → tenant_id)

User 1:many AuditEvent (user_id → actor_id)
User 1:many Invitation (user_id → invited_by)
```

## API Integration Patterns

### Resource URLs

```text
Users:         /api/v1/users
Tenants:       /api/v1/tenants
Policies:      /api/v1/policies
FeatureFlags:  /api/v1/feature-flags
Invitations:   /api/v1/invitations
AuditEvents:   /api/v1/audit-events
```

### Query Parameters

All list endpoints support:

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 25, max: 100)
- `sort`: Sort field (default: created_at)
- `order`: Sort direction ('asc' | 'desc', default: 'desc')
- `filter`: Resource-specific filters

Tenant-scoped resources include:

- `tenant_id`: Explicit tenant filter (required for superadmin)

### Response Formats

**List Response**:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 150,
    "total_pages": 6
  }
}
```

**Single Resource Response**:

```json
{
  "data": { ... }
}
```

**Error Response**:

```json
{
  "error": {
    "message": "Validation failed",
    "code": "VALIDATION_ERROR",
    "details": {
      "email": ["Email is required"]
    }
  }
}
```

## Next Steps

1. Generate OpenAPI contracts from these models
2. Create TypeScript interfaces file
3. Implement React-admin dataProvider integration
4. Generate failing contract tests
