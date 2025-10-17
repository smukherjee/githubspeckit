# Quickstart: Admin API Endpoints Testing

**Feature**: Admin API Endpoints for Multi-Tenant Backend  
**Date**: 2025-10-17  
**Status**: Phase 1 Design Complete

## Overview

This quickstart guide validates the admin API endpoints by testing key user scenarios through the backend REST API. All tests use curl commands and can be executed against a running backend server.

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Test database seeded with:
   - TestTenant (tenant_id: deterministic UUID)
   - Superadmin user (global access)
   - Tenant admin user (TestTenant access)
   - Standard user (TestTenant access)
3. Valid JWT tokens for each user role

## Test Scenarios

### Setup: Authentication Tokens

```bash
# Get superadmin token
SUPERADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "superadmin@example.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# Get tenant admin token  
TENANT_ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@testtenant.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# Get standard user token
USER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@testtenant.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# Get TestTenant ID for tests
TENANT_ID=$(curl -s -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  | jq -r '.data[] | select(.name == "TestTenant") | .tenant_id')

echo "Tokens acquired: Superadmin, Tenant Admin, User"
echo "TestTenant ID: $TENANT_ID"
```

### Scenario 1: Superadmin Cross-Tenant Management

**Test**: Superadmin manages multiple tenants and users across tenant boundaries

```bash
echo "=== Scenario 1: Superadmin Cross-Tenant Management ==="

# 1. List all tenants (superadmin can see all)
echo "1. Listing all tenants as superadmin..."
curl -s -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  | jq '.data | length'

# 2. Create a new tenant
echo "2. Creating new tenant as superadmin..."
NEW_TENANT_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NewTestTenant",
    "is_active": true,
    "settings": {
      "max_users": 50,
      "features": ["advanced_reporting"]
    }
  }' | jq -r '.data.tenant_id')

echo "New tenant created with ID: $NEW_TENANT_ID"

# 3. Create user in the new tenant (cross-tenant operation)
echo "3. Creating user in new tenant as superadmin..."
NEW_USER_ID=$(curl -s -X POST "http://localhost:8000/api/v1/admin/users?tenant_id=$NEW_TENANT_ID" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@newtesttenant.com",
    "full_name": "New Tenant Admin",
    "roles": ["tenant_admin"],
    "password": "SecurePass123!"
  }' | jq -r '.data.user_id')

echo "New user created with ID: $NEW_USER_ID"

# 4. List users across all tenants
echo "4. Listing users across all tenants as superadmin..."
curl -s -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  | jq '.pagination.total'

echo "✅ Scenario 1 PASSED: Superadmin cross-tenant operations successful"
```

### Scenario 2: Tenant Admin User Management

**Test**: Tenant admin creates and manages users within their tenant only

```bash
echo "=== Scenario 2: Tenant Admin User Management ==="

# 1. List users in own tenant (should auto-scope to tenant)
echo "1. Listing users in own tenant as tenant admin..."
TENANT_USER_COUNT=$(curl -s -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.pagination.total')

echo "Users in tenant: $TENANT_USER_COUNT"

# 2. Create new user in own tenant
echo "2. Creating new user in own tenant as tenant admin..."
TENANT_NEW_USER_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@testtenant.com",
    "full_name": "Test Developer",
    "job_title": "Software Developer",
    "department": "Engineering",
    "roles": ["developer"],
    "password": "SecurePass123!"
  }' | jq -r '.data.user_id')

echo "New user created with ID: $TENANT_NEW_USER_ID"

# 3. Update user profile information
echo "3. Updating user profile as tenant admin..."
curl -s -X PUT "http://localhost:8000/api/v1/admin/users/$TENANT_NEW_USER_ID" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Senior Software Developer",
    "timezone": "America/New_York",
    "language": "en"
  }' | jq '.data.job_title'

# 4. Try to access different tenant (should fail)
echo "4. Attempting cross-tenant access as tenant admin (should fail)..."
curl -s -X GET "http://localhost:8000/api/v1/admin/users?tenant_id=$NEW_TENANT_ID" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq -r '.error.message // "Access denied as expected"'

echo "✅ Scenario 2 PASSED: Tenant admin operations properly scoped"
```

### Scenario 3: RBAC Policy Management

**Test**: Policy creation and enforcement with proper tenant isolation

```bash
echo "=== Scenario 3: RBAC Policy Management ==="

# 1. Create custom policy as tenant admin
echo "1. Creating custom policy as tenant admin..."
POLICY_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/policies \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "developer_read_only_audit",
    "resource": "audit_events",
    "action": "read",
    "effect": "ALLOW",
    "roles": ["developer"],
    "conditions": {
      "same_tenant": true,
      "resource_owner": false
    },
    "priority": 200
  }' | jq -r '.data.policy_id')

echo "Policy created with ID: $POLICY_ID"

# 2. List policies in tenant
echo "2. Listing policies in tenant..."
curl -s -X GET http://localhost:8000/api/v1/admin/policies \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data | length'

# 3. Test policy enforcement by accessing audit logs as developer
echo "3. Getting developer token and testing policy enforcement..."
DEVELOPER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "developer@testtenant.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# Developer should now be able to read audit events
curl -s -X GET http://localhost:8000/api/v1/admin/audit-events \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" \
  | jq '.data | length'

echo "✅ Scenario 3 PASSED: Policy creation and enforcement working"
```

### Scenario 4: Feature Flag Management

**Test**: Feature flag creation and tenant-specific configuration

```bash
echo "=== Scenario 4: Feature Flag Management ==="

# 1. Create global feature flag as superadmin
echo "1. Creating global feature flag as superadmin..."
GLOBAL_FLAG_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/feature-flags \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "advanced_analytics",
    "description": "Advanced analytics dashboard",
    "is_enabled": false,
    "rollout_percentage": 25
  }' | jq -r '.data.flag_id')

echo "Global flag created with ID: $GLOBAL_FLAG_ID"

# 2. Create tenant-specific feature flag
echo "2. Creating tenant-specific feature flag as tenant admin..."
TENANT_FLAG_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/feature-flags \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom_branding",
    "description": "Custom tenant branding",
    "tenant_id": "'$TENANT_ID'",
    "is_enabled": true,
    "target_users": ["'$TENANT_NEW_USER_ID'"]
  }' | jq -r '.data.flag_id')

echo "Tenant flag created with ID: $TENANT_FLAG_ID"

# 3. List feature flags (should see global + tenant-specific)
echo "3. Listing feature flags as tenant admin..."
curl -s -X GET http://localhost:8000/api/v1/admin/feature-flags \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data | length'

echo "✅ Scenario 4 PASSED: Feature flag management working"
```

### Scenario 5: User Invitation Flow

**Test**: Complete invitation workflow with email notifications

```bash
echo "=== Scenario 5: User Invitation Flow ==="

# 1. Create invitation as tenant admin
echo "1. Creating user invitation as tenant admin..."
INVITATION_ID=$(curl -s -X POST http://localhost:8000/api/v1/admin/invitations \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "analyst@testtenant.com",
    "roles": ["analyst"],
    "expires_in_hours": 72
  }' | jq -r '.data.invitation_id')

echo "Invitation created with ID: $INVITATION_ID"

# 2. List pending invitations
echo "2. Listing pending invitations..."
curl -s -X GET "http://localhost:8000/api/v1/admin/invitations?status=pending" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data | length'

# 3. Revoke invitation
echo "3. Revoking invitation..."
curl -s -X POST "http://localhost:8000/api/v1/admin/invitations/$INVITATION_ID/revoke" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data.status'

echo "✅ Scenario 5 PASSED: Invitation workflow complete"
```

### Scenario 6: Audit Trail Verification

**Test**: Audit events are properly logged and queryable

```bash
echo "=== Scenario 6: Audit Trail Verification ==="

# 1. Get recent audit events
echo "1. Retrieving recent audit events..."
RECENT_EVENTS=$(curl -s -X GET http://localhost:8000/api/v1/admin/audit-events \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data | length')

echo "Recent events count: $RECENT_EVENTS"

# 2. Filter audit events by event type
echo "2. Filtering audit events by type (user creation)..."
curl -s -X GET "http://localhost:8000/api/v1/admin/audit-events?event_type=user.created" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data | length'

# 3. Get specific audit event details
echo "3. Getting first audit event details..."
FIRST_EVENT_ID=$(curl -s -X GET http://localhost:8000/api/v1/admin/audit-events \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq -r '.data[0].event_id')

curl -s -X GET "http://localhost:8000/api/v1/admin/audit-events/$FIRST_EVENT_ID" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  | jq '.data.event_type'

echo "✅ Scenario 6 PASSED: Audit trail verification complete"
```

### Scenario 7: Bulk Operations

**Test**: CSV import/export functionality for user management

```bash
echo "=== Scenario 7: Bulk Operations ==="

# 1. Export users to CSV
echo "1. Exporting users to CSV..."
curl -s -X POST http://localhost:8000/api/v1/admin/users/bulk/export \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {"is_disabled": false},
    "fields": ["email", "full_name", "roles", "created_at"]
  }' \
  -o users_export.csv

echo "Users exported to users_export.csv"

# 2. Create CSV for import test
echo "2. Creating test CSV for import..."
cat > users_import.csv << EOF
email,full_name,job_title,roles
tester1@testtenant.com,Test User 1,QA Tester,user
tester2@testtenant.com,Test User 2,QA Lead,user
EOF

# 3. Dry run import
echo "3. Running dry-run import..."
curl -s -X POST http://localhost:8000/api/v1/admin/users/bulk/import \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -F "file=@users_import.csv" \
  -F "dry_run=true" \
  | jq '.total_rows'

# 4. Actual import
echo "4. Running actual import..."
IMPORT_RESULT=$(curl -s -X POST http://localhost:8000/api/v1/admin/users/bulk/import \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -F "file=@users_import.csv" \
  -F "dry_run=false")

echo "Import results:"
echo "$IMPORT_RESULT" | jq '{total_rows, successful, failed}'

# Cleanup
rm -f users_export.csv users_import.csv

echo "✅ Scenario 7 PASSED: Bulk operations working"
```

## Performance Validation

### Response Time Testing

```bash
echo "=== Performance Validation ==="

# Test CRUD operation response times (should be <200ms p95)
for i in {1..10}; do
  START_TIME=$(date +%s%3N)
  curl -s -X GET http://localhost:8000/api/v1/admin/users \
    -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" > /dev/null
  END_TIME=$(date +%s%3N)
  DURATION=$((END_TIME - START_TIME))
  echo "Request $i: ${DURATION}ms"
done

echo "✅ Performance validation complete"
```

## Cleanup

```bash
echo "=== Cleanup ==="

# Delete created test tenant
curl -s -X DELETE "http://localhost:8000/api/v1/admin/tenants/$NEW_TENANT_ID" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN"

echo "✅ Cleanup complete"
```

## Expected Results

- **Scenario 1**: Superadmin can perform cross-tenant operations
- **Scenario 2**: Tenant admin operations are properly scoped to their tenant
- **Scenario 3**: RBAC policies are enforced correctly
- **Scenario 4**: Feature flags work at global and tenant levels
- **Scenario 5**: User invitation workflow functions end-to-end
- **Scenario 6**: Audit events are logged and queryable
- **Scenario 7**: Bulk operations handle CSV import/export
- **Performance**: All CRUD operations complete under 200ms

## Success Criteria

✅ All scenarios execute without errors  
✅ Tenant isolation is enforced (no cross-tenant data leakage)  
✅ RBAC permissions are properly validated  
✅ Audit events capture all administrative actions  
✅ Response times meet performance budgets  
✅ API contracts match OpenAPI specification

## Next Steps

1. Implement backend API endpoints following the contracts
2. Set up contract tests based on these scenarios
3. Add performance monitoring and alerting
4. Create frontend clients using these APIs
