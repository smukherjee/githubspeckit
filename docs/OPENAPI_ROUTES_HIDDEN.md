# OpenAPI Routes Hidden - Summary

## Date: October 20, 2025

## Objective
Comment out feature-flags and policies API routes so they don't appear in the OpenAPI documentation.

## Changes Made

### 1. Main App Router Registration (`src/adapters/api/app.py`)

#### Commented out imports:
- Line 30: `# from adapters.api.routers import policies as policies_router  # Hidden from OpenAPI docs`
- Line 31: `# from adapters.api.routers import feature_flags as feature_flags_router  # Hidden from OpenAPI docs`

#### Commented out router includes:
- Line 287: `# app.include_router(policies_router.router, prefix="/api")  # Hidden from OpenAPI docs`
- Line 288: `# app.include_router(feature_flags_router.router, prefix="/api")  # Hidden from OpenAPI docs`

### 2. Tenant-Scoped Router (`src/adapters/api/routers/tenants/__init__.py`)

#### Commented out import:
- `# from .policies import router as policies_router  # Hidden from OpenAPI docs`

#### Commented out router include:
- `# router.include_router(policies_router)  # Hidden from OpenAPI docs`

## Files Modified
1. `/Users/sujoymukherjee/code/githubspeckit/src/adapters/api/app.py`
2. `/Users/sujoymukherjee/code/githubspeckit/src/adapters/api/routers/tenants/__init__.py`

## Files Backed Up
- `/Users/sujoymukherjee/code/githubspeckit/src/adapters/api/app.py.backup` (original copy before changes)

## Routes Hidden from OpenAPI

### Feature Flags Routes (Previously at `/api/v1/feature-flags`)
- `POST /api/v1/feature-flags` - Create feature flag
- `GET /api/v1/feature-flags` - List feature flags by tenant

### Policies Routes (Previously at `/api/v1/policies`)
- `POST /api/v1/policies/dry-run` - Policy dry-run evaluation
- `POST /api/v1/policies/register` - Register policy
- `GET /api/v1/policies` - List policies
- `PUT /api/v1/policies/{policy_id}/disable` - Disable policy
- `PUT /api/v1/policies/{policy_id}/enable` - Enable policy
- `DELETE /api/v1/policies/{policy_id}` - Delete policy

### Tenant-Scoped Policies Routes (Previously at `/api/v1/tenants/{tenant_id}/policies`)
- All tenant-scoped policy management endpoints

## Impact Assessment

### ✅ Positive Impacts
- Feature flags and policies routes will NOT appear in OpenAPI/Swagger documentation
- Routes are effectively disabled (commented out, not deleted)
- Easy to re-enable by uncommenting the lines
- Original router files remain intact and unchanged

### ⚠️ Considerations
- Any existing API clients using these endpoints will receive 404 errors
- Tests that rely on these endpoints may fail
- Frontend code accessing these routes will need to be updated or removed

## Testing Recommendations

1. **Verify OpenAPI docs**: Check `/docs` endpoint to ensure feature-flags and policies routes are not listed
2. **Run test suite**: Execute tests to identify any failures related to commented routes
3. **Update frontend**: Remove or comment out frontend code that calls these endpoints
4. **Update API documentation**: Note the removal of these endpoints in any external API documentation

## Rollback Instructions

To re-enable these routes:

1. Restore from backup:
   ```bash
   cp /Users/sujoymukherjee/code/githubspeckit/src/adapters/api/app.py.backup /Users/sujoymukherjee/code/githubspeckit/src/adapters/api/app.py
   ```

2. Or manually uncomment the lines by removing the `#` and "Hidden from OpenAPI docs" comments

## Notes
- The actual router implementation files were NOT modified:
  - `src/adapters/api/routers/feature_flags.py` (unchanged)
  - `src/adapters/api/routers/policies.py` (unchanged)
  - `src/adapters/api/routers/tenants/policies.py` (unchanged)
- Only the router registration/includes were commented out
- This approach maintains code integrity while hiding routes from OpenAPI docs
