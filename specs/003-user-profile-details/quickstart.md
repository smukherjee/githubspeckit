# Quickstart: User Profile Details

**Feature**: User Profile Details with Photo Upload  
**Last Updated**: 2025-01-17  
**Status**: Design Complete (Phase 1)

## Overview

This quickstart guide demonstrates how to use the User Profile Details API to manage user profile information (name, phone, address) and profile photos with WhatsApp-style optimization (640px display, 96px thumbnail, 48px avatar).

## Prerequisites

- **Backend running**: `make server-start` (runs on <http://localhost:8000>)
- **Database seeded**: `make db-seed` (creates `infysightsa@infysight.com` superadmin)
- **Auth token**: Obtain JWT from login endpoint

## Authentication Flow

### 1. Login to Get JWT Token

```bash
# Login as superadmin
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "infysightsa@infysight.com",
    "password": "infysightsa123"
  }'
```

**Response**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
    "email": "infysightsa@infysight.com",
    "role": "superadmin",
    "tenant_id": "c79911ec-beb1-5c45-833d-4a9847b88024",
    "status": "active"
  }
}
```

**Save token for subsequent requests**:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export USER_ID="a5053ec7-a656-53ef-98c4-8713a68b2b9b"
```

## Profile Management Scenarios

### Scenario 1: Create New Profile (First-Time User)

**Happy Path**: User completes profile after registration.

#### Step 1: Check if profile exists

```bash
curl -X GET "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response** (404 if not created yet):

```json
{
  "error": "not_found",
  "message": "User profile not found"
}
```

#### Step 2: Create profile with full details

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Sarah Johnson",
    "phone": "+1-555-987-6543",
    "address": "456 Oak Avenue\nSuite 200\nBoston, MA 02108"
  }'
```

**Expected Response** (200 OK):

```json
{
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "full_name": "Sarah Johnson",
  "phone": "+1-555-987-6543",
  "address": "456 Oak Avenue\nSuite 200\nBoston, MA 02108",
  "photo_display_url": null,
  "photo_thumbnail_url": null,
  "photo_avatar_url": null,
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T10:30:00Z"
}
```

**Verify creation**:

```bash
curl -X GET "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 2: Update Existing Profile (Partial Update)

**Use Case**: User changes phone number only.

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1-617-555-1234"
  }'
```

**Expected Response** (200 OK):

```json
{
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "full_name": "Sarah Johnson",
  "phone": "+1-617-555-1234",
  "address": "456 Oak Avenue\nSuite 200\nBoston, MA 02108",
  "photo_display_url": null,
  "photo_thumbnail_url": null,
  "photo_avatar_url": null,
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T14:22:00Z"
}
```

**Note**: Other fields (full_name, address) remain unchanged.

### Scenario 3: Clear Optional Fields

**Use Case**: User removes phone and address (privacy).

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": null,
    "address": null
  }'
```

**Expected Response** (200 OK):

```json
{
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "full_name": "Sarah Johnson",
  "phone": null,
  "address": null,
  "photo_display_url": null,
  "photo_thumbnail_url": null,
  "photo_avatar_url": null,
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T15:10:00Z"
}
```

## Photo Upload Scenarios

### Scenario 4: Upload Profile Photo (Async Processing)

**Use Case**: User uploads profile photo, system generates 3 optimized variants.

#### Step 1: Upload photo (multipart/form-data)

```bash
# Prepare test photo (or use existing image)
wget -O test-photo.jpg https://picsum.photos/1200/1200

# Upload photo
curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/profile/photo" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-photo.jpg"
```

**Expected Response** (202 Accepted):

```json
{
  "message": "Photo upload started",
  "status": "processing",
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b"
}
```

**Note**: Processing happens in background (FastAPI BackgroundTasks). Expected duration: ~1.8s for 5MB photo.

#### Step 2: Wait for processing (poll or wait ~2-3 seconds)

```bash
sleep 3
```

#### Step 3: Verify photo URLs in profile

```bash
curl -X GET "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response** (200 OK):

```json
{
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "full_name": "Sarah Johnson",
  "phone": null,
  "address": null,
  "photo_display_url": "http://localhost:8000/media/photos/a5053ec7-a656-53ef-98c4-8713a68b2b9b/display.jpg",
  "photo_thumbnail_url": "http://localhost:8000/media/photos/a5053ec7-a656-53ef-98c4-8713a68b2b9b/thumbnail.jpg",
  "photo_avatar_url": "http://localhost:8000/media/photos/a5053ec7-a656-53ef-98c4-8713a68b2b9b/avatar.jpg",
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T15:45:30Z"
}
```

**Photo Processing Details**:

- **Display**: 640x640px, JPEG quality 85%, ~200KB
- **Thumbnail**: 96x96px, JPEG quality 80%, ~15KB
- **Avatar**: 48x48px, JPEG quality 75%, ~5KB
- **Algorithm**: Center crop to square, LANCZOS resize
- **Security**: EXIF metadata stripped, magic bytes validated

#### Step 4: View photos in browser

```bash
# Display photo (640x640px)
open "http://localhost:8000/media/photos/$USER_ID/display.jpg"

# Thumbnail (96x96px)
open "http://localhost:8000/media/photos/$USER_ID/thumbnail.jpg"

# Avatar (48x48px)
open "http://localhost:8000/media/photos/$USER_ID/avatar.jpg"
```

### Scenario 5: Replace Existing Photo

**Use Case**: User uploads new photo to replace old one.

```bash
# Upload new photo (same endpoint, overwrites previous)
curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/profile/photo" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@new-photo.png"
```

**Expected Response** (202 Accepted):

```json
{
  "message": "Photo upload started",
  "status": "processing",
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b"
}
```

**Note**: Old photo files deleted (or marked for garbage collection), new URLs generated.

### Scenario 6: Remove Profile Photo

**Use Case**: User deletes profile photo.

```bash
curl -X DELETE "http://localhost:8000/api/v1/users/$USER_ID/profile/photo" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response** (204 No Content):

```http
HTTP/1.1 204 No Content
```

**Verify photo removed**:

```bash
curl -X GET "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response** (photo URLs are null):

```json
{
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "full_name": "Sarah Johnson",
  "phone": null,
  "address": null,
  "photo_display_url": null,
  "photo_thumbnail_url": null,
  "photo_avatar_url": null,
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T16:10:00Z"
}
```

## RBAC & Tenant Isolation Scenarios

### Scenario 7: Regular User Access (Own Profile Only)

**Setup**: Login as regular user.

```bash
# Create test user (tenant_admin or superadmin can do this)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@infysight.com",
    "role": "user"
  }'

# Response includes user_id (e.g., "abc123...")
export TEST_USER_ID="abc123..."

# Reset password for test user (activates account)
curl -X POST "http://localhost:8000/api/v1/users/$TEST_USER_ID/reset-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "TestUser123!"
  }'

# Login as test user
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@infysight.com",
    "password": "TestUser123!"
  }'

# Save test user token
export TEST_TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

**Test 1: User can update own profile**:

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe"
  }'
```

**Expected Response** (200 OK): Profile updated successfully.

**Test 2: User cannot update other user's profile**:

```bash
# Try to update superadmin's profile
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Hacked!"
  }'
```

**Expected Response** (403 Forbidden):

```json
{
  "error": "forbidden",
  "message": "Insufficient permissions to access this resource"
}
```

### Scenario 8: Tenant Admin Access (Same Tenant Only)

**Use Case**: Tenant admin can manage profiles within their tenant.

```bash
# Create tenant admin user (superadmin does this)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@infysight.com",
    "role": "tenant_admin"
  }'

export ADMIN_USER_ID="def456..."

# Activate tenant admin
curl -X POST "http://localhost:8000/api/v1/users/$ADMIN_USER_ID/reset-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "AdminUser123!"
  }'

# Login as tenant admin
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@infysight.com",
    "password": "AdminUser123!"
  }'

export ADMIN_TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

**Test 1: Tenant admin can update tenant user's profile**:

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1-555-000-1111"
  }'
```

**Expected Response** (200 OK): Profile updated successfully.

**Test 2: Tenant admin cannot update cross-tenant profile**:

```bash
# Create user in different tenant (superadmin only)
# ... (setup another tenant, create user there)
# Tenant admin tries to access cross-tenant user

curl -X GET "http://localhost:8000/api/v1/users/OTHER_TENANT_USER_ID/profile" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response** (403 Forbidden):

```json
{
  "error": "forbidden",
  "message": "Access denied - user belongs to different tenant"
}
```

### Scenario 9: Superadmin Access (All Profiles)

**Use Case**: Superadmin can manage all profiles across all tenants.

```bash
# Superadmin can update any profile (same or different tenant)
curl -X PUT "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Updated by superadmin"
  }'
```

**Expected Response** (200 OK): Profile updated successfully.

## Validation Scenarios

### Scenario 10: Invalid Phone Number

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "abc"
  }'
```

**Expected Response** (422 Unprocessable Entity):

```json
{
  "error": "validation_error",
  "message": "Validation failed",
  "details": [
    {
      "field": "phone",
      "issue": "Phone must contain at least 7 digits"
    }
  ]
}
```

### Scenario 11: Address Too Long

```bash
curl -X PUT "http://localhost:8000/api/v1/users/$USER_ID/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "'$(python3 -c "print('x' * 501)")'"
  }'
```

**Expected Response** (422 Unprocessable Entity):

```json
{
  "error": "validation_error",
  "message": "Validation failed",
  "details": [
    {
      "field": "address",
      "issue": "Address must not exceed 500 characters"
    }
  ]
}
```

### Scenario 12: Invalid Photo Format

```bash
# Upload PDF file (not an image)
echo "%PDF-1.4" > fake-photo.pdf

curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/profile/photo" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@fake-photo.pdf"
```

**Expected Response** (400 Bad Request):

```json
{
  "error": "validation_error",
  "message": "Invalid file format",
  "details": [
    {
      "field": "file",
      "issue": "File type application/pdf not supported. Allowed types: JPEG, PNG, WebP, GIF"
    }
  ]
}
```

### Scenario 13: Photo File Too Large

```bash
# Create 15MB file (exceeds 10MB limit)
dd if=/dev/urandom of=large-photo.jpg bs=1M count=15

curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/profile/photo" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@large-photo.jpg"
```

**Expected Response** (413 Payload Too Large):

```json
{
  "error": "payload_too_large",
  "message: "Request entity too large",
  "details": [
    {
      "issue": "Maximum request size is 10MB"
    }
  ]
}
```

## Integration Testing

### Complete End-to-End Flow

#### Scenario 14: New User Journey (Profile Completion)

1. **User registers** → Receives invitation email
2. **User sets password** → Account activated
3. **User logs in** → Receives JWT token
4. **User creates profile** → Updates name, phone, address
5. **User uploads photo** → System generates 3 variants
6. **User views profile** → All fields populated
7. **User edits profile** → Updates phone number
8. **Admin views user profile** → Sees complete details

```bash
# Step 1-3: Registration, password reset, login (covered above)

# Step 4: Create profile
curl -X PUT "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "phone": "+1-617-555-9876",
    "address": "789 Elm St\nCambridge, MA 02139"
  }'

# Step 5: Upload photo
curl -X POST "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile/photo" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -F "file=@test-photo.jpg"

# Wait for processing
sleep 3

# Step 6: View complete profile
curl -X GET "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $TEST_TOKEN"

# Step 7: Edit profile
curl -X PUT "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1-617-555-0000"
  }'

# Step 8: Admin views profile
curl -X GET "http://localhost:8000/api/v1/users/$TEST_USER_ID/profile" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected**: All operations succeed, profile complete with photo variants.

## Performance Expectations

Based on research (specs/003-user-profile-details/research.md):

| Operation | Target (p95) | Notes |
|-----------|--------------|-------|
| GET profile | <200ms | Database query + serialization |
| PUT profile | <200ms | Validation + database upsert |
| POST photo | <5s | Async processing (3 variants) |
| DELETE photo | <200ms | Database update (URLs → null) |

**Photo Processing Breakdown** (5MB input):

- Upload receive: ~500ms
- Validation (magic bytes): ~50ms
- Resize 3 variants: ~1.2s
- Storage write: ~200ms
- Database update: ~50ms
- **Total**: ~2s (under 5s target)

## Troubleshooting

### Issue: Photo upload returns 400 "Cannot identify image format"

**Cause**: File is corrupted or not a valid image.

**Solution**: Verify file with `file` command:

```bash
file test-photo.jpg
# Output: test-photo.jpg: JPEG image data, ...
```

### Issue: Profile update returns 403 Forbidden

**Cause**: User trying to update profile in different tenant.

**Solution**: Verify token tenant_id matches user tenant_id:

```bash
# Decode JWT (requires jq and base64)
echo $TOKEN | cut -d. -f2 | base64 -d | jq .

# Check tenant_id in response
```

### Issue: Photo URLs return 404 after upload

**Cause**: Background processing not complete or storage path misconfigured.

**Solution**:

1. Wait longer (2-3 seconds) before checking
2. Check server logs for processing errors
3. Verify storage configuration (local FS path or S3 credentials)

```bash
# Check logs
tail -f logs/app.log | grep "photo processing"
```

### Issue: Phone validation fails for valid number

**Cause**: Phone format too strict or too loose.

**Solution**: Adjust validation pattern (7-20 chars, ≥7 digits):

```bash
# Valid formats
+1-555-123-4567  ✅
(617) 555-9876   ✅
555.123.4567     ✅
+44 20 1234 5678 ✅

# Invalid formats
123              ❌ (too short)
abcdefghijk      ❌ (no digits)
```

## Next Steps

1. **Contract Tests**: Run failing tests (TDD red phase)
2. **Implementation**: Follow task plan (Phase 2)
3. **Integration**: Wire domain → adapter → API layers
4. **Performance Testing**: Verify <5s p95 photo processing
5. **Load Testing**: 100 concurrent photo uploads

## Reference Documentation

- **Feature Spec**: `specs/003-user-profile-details/spec.md`
- **Data Model**: `specs/003-user-profile-details/data-model.md`
- **OpenAPI Contract**: `specs/003-user-profile-details/contracts/openapi-user-profile.yaml`
- **Research & Decisions**: `specs/003-user-profile-details/research.md`
- **Implementation Plan**: `specs/003-user-profile-details/plan.md`
