# Admin Password Reset API

**Feature**: Admin-initiated password reset endpoint  
**Date**: 2025-10-17  
**Status**: Implemented  
**Related**: FR-019 (RBAC), FR-003 (User Management)

## Overview

The admin password reset endpoint allows tenant administrators and superadmins to reset user passwords directly without requiring email-based self-service flows. This is useful for:

- **Account recovery**: When users are locked out
- **Security incidents**: Forcing password changes after breaches
- **Onboarding**: Activating invited users by setting their initial password
- **Support scenarios**: Helping users who forgot passwords

## Endpoint

```http
POST /api/v1/users/{user_id}/reset-password
```

### Authentication

**Required**: Bearer token (JWT)

### Authorization (RBAC)

| Role | Scope |
|------|-------|
| **superadmin** | Can reset password for ANY user in ANY tenant |
| **tenant_admin** | Can reset password for users in THEIR OWN tenant only |
| **Other roles** | ❌ Forbidden (403) |

### Special Rules

1. **Superadmin protection**: Only superadmins can reset another superadmin's password
2. **Tenant isolation**: Tenant admins cannot reset passwords across tenant boundaries
3. **Auto-activation**: Resetting password for an `invited` user activates them (`status: active`)

## Request

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | UUID string | The ID of the user whose password will be reset |

### Request Body

```json
{
  "new_password": "string"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `new_password` | string | ✅ Yes | Min 8 chars, requires uppercase, lowercase, and digit |

### Password Strength Requirements

The password MUST meet the following criteria:

- ✅ At least 8 characters long
- ✅ Contains at least one uppercase letter (A-Z)
- ✅ Contains at least one lowercase letter (a-z)
- ✅ Contains at least one digit (0-9)

**Examples**:

| Password | Valid? | Reason |
|----------|--------|--------|
| `Password123` | ✅ Yes | Meets all requirements |
| `weak` | ❌ No | Too short |
| `lowercase123` | ❌ No | Missing uppercase |
| `UPPERCASE123` | ❌ No | Missing lowercase |
| `NoDigitsHere` | ❌ No | Missing digit |

## Responses

### Success (200 OK)

```json
{
  "message": "Password reset successfully",
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b"
}
```

### Error Responses

#### 401 Unauthorized

Missing or invalid JWT token.

```json
{
  "detail": "Invalid or expired token"
}
```

#### 403 Forbidden

Insufficient permissions to reset passwords.

```json
{
  "detail": "Only tenant admins and superadmins can reset user passwords"
}
```

Or when trying to reset a superadmin password as a tenant admin:

```json
{
  "detail": "Only superadmins can reset superadmin passwords"
}
```

Or when trying to reset a user in another tenant:

```json
{
  "detail": "Cannot reset passwords for users in other tenants"
}
```

#### 404 Not Found

User does not exist.

```json
{
  "detail": "user_not_found"
}
```

#### 422 Validation Error

Password does not meet strength requirements.

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "new_password"],
      "msg": "Value error, Password must be at least 8 characters long",
      "input": "weak",
      "ctx": {
        "error": {}
      }
    }
  ]
}
```

## Usage Examples

### Example 1: Superadmin resets a user's password

```bash
# Login as superadmin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "infysightsa@infysight.com", "password": "infysightsa123"}' \
  | jq -r '.access_token')

# Reset user password
curl -X POST http://localhost:8000/api/v1/users/28aa6bae-d6fa-44d5-b514-6bbf0fab7d7a/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "NewSecurePassword123"}'
```

**Response**:

```json
{
  "message": "Password reset successfully",
  "user_id": "28aa6bae-d6fa-44d5-b514-6bbf0fab7d7a"
}
```

### Example 2: Tenant admin resets password in their tenant

```bash
# Login as tenant admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@company.com", "password": "AdminPassword123"}' \
  | jq -r '.access_token')

# Reset user password (same tenant)
curl -X POST http://localhost:8000/api/v1/users/user-id-here/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "ResetPassword456"}'
```

### Example 3: Activate invited user by setting password

```bash
# User was created without password (invited status)
# Admin sets password to activate them

curl -X POST http://localhost:8000/api/v1/users/invited-user-id/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "ActivationPassword789"}'
```

**Result**: User status changes from `invited` → `active` and can now login.

### Example 4: Regular user tries to reset password (fails)

```bash
# Login as regular user
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@company.com", "password": "UserPassword123"}' \
  | jq -r '.access_token')

# Try to reset another user's password
curl -X POST http://localhost:8000/api/v1/users/other-user-id/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "HackedPassword123"}'
```

**Response** (403 Forbidden):

```json
{
  "detail": "Only tenant admins and superadmins can reset user passwords"
}
```

## Implementation Details

### Code Location

- **Router**: `src/adapters/api/routers/users.py`
- **Endpoint Function**: `reset_user_password()`
- **Validation**: `validate_password_strength()` (shared with user creation)
- **Tests**: `tests/api/integration/test_user_management.py::TestPasswordReset`

### RBAC Enforcement Flow

```python
# 1. Check role permission
if not (current_user.has_role("tenant_admin") or current_user.is_superadmin()):
    raise HTTPException(403, "Only tenant admins and superadmins...")

# 2. Check tenant isolation (unless superadmin)
if target_user.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
    raise HTTPException(403, "Cannot reset passwords for users in other tenants")

# 3. Protect superadmin accounts
if "superadmin" in target_user.roles and not current_user.is_superadmin():
    raise HTTPException(403, "Only superadmins can reset superadmin passwords")
```

### Database Updates

When password is reset:

1. **password_hash**: Updated with Argon2id hash of new password
2. **updated_at**: Set to current UTC timestamp
3. **updated_by**: Set to current user's ID (audit trail)
4. **status**: If `invited`, changed to `active`

## Comparison with Self-Service Password Reset

| Feature | Admin Reset | Self-Service Reset |
|---------|-------------|-------------------|
| **Endpoint** | `POST /users/{id}/reset-password` | `POST /auth/password/reset` + `/auth/password/confirm` |
| **Authentication** | Required (admin) | Not required (email-based) |
| **Authorization** | tenant_admin or superadmin | Any user with valid email |
| **Flow** | Direct password change | Email → token → confirm |
| **Use Case** | Admin assistance | User forgot password |
| **Status** | ✅ Implemented | ⏳ Not yet implemented |

**Note**: Self-service password reset (`/auth/password/reset`) is specified in the OpenAPI contract but not yet implemented. It would use the `password_reset_requests` table for token management.

## Security Considerations

### Audit Trail

All password resets are tracked via:

- **updated_by**: User ID of the admin who performed the reset
- **updated_at**: Timestamp of the password change
- Future enhancement: Emit audit events to `audit_events` table

### Token Invalidation

**Current Behavior**: Existing JWT tokens remain valid after password reset.

**Recommended Enhancement**: Implement token revocation by:

1. Recording password change timestamp in user record
2. Validating `iat` (issued at) claim against password change timestamp
3. Rejecting tokens issued before password change

### Rate Limiting

**Recommended**: Add rate limiting to prevent brute-force attacks:

- Max 5 password reset attempts per user per hour
- Max 50 password resets per admin per hour

## Testing

### Test Coverage

✅ 6 integration tests in `tests/api/integration/test_user_management.py`:

1. `test_superadmin_can_reset_any_user_password` - Verify superadmin access
2. `test_reset_password_validates_strength` - Password length validation
3. `test_reset_password_validates_password_complexity` - Uppercase/lowercase/digit validation
4. `test_regular_user_cannot_reset_password` - RBAC enforcement (403)
5. `test_reset_nonexistent_user_fails` - 404 for invalid user_id
6. `test_reset_password_activates_invited_user` - Auto-activation feature

### Running Tests

```bash
# Run all password reset tests
pytest tests/api/integration/test_user_management.py::TestPasswordReset -v

# Run with database
DATABASE_URL="postgresql+asyncpg://..." \
  pytest tests/api/integration/test_user_management.py::TestPasswordReset -v
```

All tests pass ✅

## Related Documentation

- **User Management**: `docs/api/users.md` (if exists)
- **Authentication**: `docs/AUTHENTICATION_IMPLEMENTATION_COMPLETE.md`
- **RBAC**: `docs/RBAC_AND_TENANT_ISOLATION_COMPLETE.md`
- **OpenAPI Spec**: `specs/001-modern-enterprise-grade/contracts/openapi-base.yaml`

## Future Enhancements

1. **Self-service password reset**: Implement `/auth/password/reset` and `/auth/password/confirm`
2. **Password history**: Prevent reusing last N passwords
3. **Force password change**: Add `must_change_password` flag
4. **Audit events**: Emit `password_reset` event to audit log
5. **Token invalidation**: Revoke existing tokens on password change
6. **Rate limiting**: Prevent abuse of reset endpoint
7. **MFA requirement**: Require MFA for sensitive password resets
