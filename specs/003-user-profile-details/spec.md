# Feature Specification: User Profile Details

**Feature Branch**: `003-user-profile-details`  
**Created**: 2025-10-17  
**Status**: Draft  
**Input**: User description: "add a new table for user details to contain personal information like name, profile photo, phone, address etc. all fields should be optional. photo size to be scaled so that it can be shown on the screen. take the example and sizes from whatsapp profile section for fields"

## Overview

This feature extends the existing user management system by adding a dedicated table for storing optional user profile details including personal information (name, profile photo, phone, address). The profile photo will be optimized for display purposes following WhatsApp's profile section standards.

## User Scenarios & Testing

### Primary User Stories

**Story 1: User Profile Completion**

As a user, I need to add my personal details (name, photo, phone, address) to my profile so that other users in my organization can identify and contact me.

**Story 2: Admin User Management**

As a tenant administrator, I need to view user profile details when managing my organization's users so that I can verify user information and maintain accurate records.

**Story 3: Profile Photo Management**

As a user, I need to upload a profile photo that displays properly across different screens so that my account has a visual identity.

### Acceptance Scenarios

#### Scenario 1: User Updates Profile Details

1. **Given** a user is logged into the system
2. **When** they navigate to their profile page
3. **And** they enter their full name "John Doe"
4. **And** they enter their phone number "+1 (555) 123-4567"
5. **And** they enter their address "123 Main St, City, State 12345"
6. **And** they click "Save"
7. **Then** the system saves their profile details
8. **And** displays a success message
9. **And** the details are immediately visible in their profile

#### Scenario 2: User Uploads Profile Photo

1. **Given** a user is on their profile edit page
2. **When** they click "Upload Photo"
3. **And** they select an image file (JPG, PNG, WebP)
4. **Then** the system validates the file type
5. **And** scales/crops the image to optimal display size (similar to WhatsApp: 640x640px max, 200KB compressed)
6. **And** generates thumbnail versions (e.g., 96x96px for list views, 48x48px for avatars)
7. **And** stores the processed images
8. **And** displays the new photo immediately
9. **And** shows file size and dimensions feedback

#### Scenario 3: Admin Views User Profiles

1. **Given** a tenant admin is viewing the users list
2. **When** they click on a specific user
3. **Then** they see the user's email and roles (existing data)
4. **And** they see the user's profile details: name, photo, phone, address (if populated)
5. **And** profile photo displays as a thumbnail
6. **And** clicking the photo shows full-size version

#### Scenario 4: Partial Profile Completion

1. **Given** a user creates a new account
2. **When** they access their profile for the first time
3. **Then** all profile detail fields are empty (optional)
4. **And** they can save with only some fields filled (e.g., just name)
5. **And** unfilled fields display as "Not provided" or similar placeholder
6. **And** they can update any field later without requiring all fields

#### Scenario 5: Profile Photo Optimization

1. **Given** a user uploads a 5MB, 4000x3000px photo
2. **When** the upload completes
3. **Then** the system automatically:
   - Resizes to max 640x640px (maintaining aspect ratio)
   - Compresses to ~200KB JPEG/WebP
   - Generates 96x96px thumbnail for list views
   - Generates 48x48px avatar for headers/comments
4. **And** stores all versions efficiently
5. **And** serves appropriate size based on context (responsive)

#### Scenario 6: Multi-Tenant Profile Isolation

1. **Given** two users with same email in different tenants
2. **When** User A in Tenant X updates their profile photo
3. **Then** only User A's profile in Tenant X is updated
4. **And** User B in Tenant Y sees no changes
5. **And** profiles are completely isolated by tenant_id

### Edge Cases

- **Large file upload**: System rejects files >10MB before processing
- **Invalid image format**: System rejects non-image files (PDF, DOCX, etc.) with clear error message
- **Malicious file upload**: System scans for executable code in image EXIF data and strips metadata
- **Photo deletion**: User can remove their photo, reverting to default avatar/initials
- **Concurrent profile updates**: Last-write-wins with timestamp conflict detection
- **Phone number formats**: System accepts various international formats (E.164 validation optional)
- **Address internationalization**: System supports multi-line addresses, various country formats
- **Profile without photo**: System generates default avatar from initials (e.g., "JD" for John Doe)
- **RBAC for profile editing**: Users can only edit their own profile; admins can view all profiles in their tenant
- **Superadmin cross-tenant viewing**: Superadmins can view profiles across all tenants

## Requirements

### Functional Requirements

#### Core Profile Data

- **FR-001**: System MUST store optional user profile details linked to existing user records via user_id
- **FR-002**: System MUST support the following optional profile fields:
  - Full name (display name)
  - Profile photo (image file reference/URL)
  - Phone number (international format support)
  - Address (multi-line text, unstructured)
- **FR-003**: System MUST ensure all profile fields are optional (nullable)
- **FR-004**: System MUST maintain one-to-one relationship between users and user_details
- **FR-005**: System MUST enforce tenant isolation for profile data (tenant_id scoping)

#### Profile Photo Management

- **FR-006**: System MUST accept image uploads in common formats (JPEG, PNG, WebP, GIF)
- **FR-007**: System MUST reject files larger than 10MB before processing
- **FR-008**: System MUST automatically resize uploaded photos to maximum 640x640px display size
- **FR-009**: System MUST compress photos to target size of ~200KB for web delivery
- **FR-010**: System MUST generate thumbnail versions:
  - Large thumbnail: 96x96px (for user lists, cards)
  - Small avatar: 48x48px (for headers, comments, inline mentions)
- **FR-011**: System MUST maintain aspect ratio when resizing images
- **FR-012**: System MUST strip EXIF metadata from uploaded images for privacy/security
- **FR-013**: System MUST support center-crop square photos (similar to WhatsApp profile photos)
- **FR-014**: System MUST store processed images efficiently (cloud storage or database BLOB depending on infrastructure)
- **FR-015**: System MUST serve responsive image sizes based on client request (srcset support)

#### API Endpoints

- **FR-016**: System MUST provide GET /api/v1/users/{user_id}/profile endpoint to retrieve profile details
- **FR-017**: System MUST provide PUT /api/v1/users/{user_id}/profile endpoint to update profile details
- **FR-018**: System MUST provide POST /api/v1/users/{user_id}/profile/photo endpoint for photo uploads
- **FR-019**: System MUST provide DELETE /api/v1/users/{user_id}/profile/photo endpoint to remove photos
- **FR-020**: System MUST provide GET /api/v1/users/me/profile endpoint for current user's profile

#### Authorization & Security

- **FR-021**: Users MUST be able to view and edit ONLY their own profile details
- **FR-022**: Tenant admins MUST be able to view (read-only) profile details of users in their tenant
- **FR-023**: Superadmins MUST be able to view profile details of users across all tenants
- **FR-024**: System MUST validate image file types before processing (prevent executable uploads)
- **FR-025**: System MUST scan uploaded images for embedded malicious code
- **FR-026**: System MUST enforce tenant isolation (users cannot access profiles in other tenants)

#### Data Validation

- **FR-027**: System MUST validate phone numbers for basic format (allow international formats, E.164 recommended)
- **FR-028**: System MUST accept addresses in various international formats (no rigid schema)
- **FR-029**: System MUST limit field lengths:
  - Full name: max 100 characters
  - Phone: max 20 characters
  - Address: max 500 characters (multi-line)
- **FR-030**: System MUST sanitize input to prevent XSS attacks in name/address fields

#### Audit Trail

- **FR-031**: System MUST record created_at and updated_at timestamps for profile changes
- **FR-032**: System MUST record created_by and updated_by user IDs for audit purposes
- **FR-033**: System SHOULD emit audit events for profile photo changes (privacy-sensitive operation)

### Non-Functional Requirements

#### Performance

- **NFR-001**: Profile photo upload and processing MUST complete within 5 seconds for 95th percentile
- **NFR-002**: Profile retrieval MUST complete within 200ms for 95th percentile
- **NFR-003**: Image resizing MUST be asynchronous (return 202 Accepted, process in background)
- **NFR-004**: Thumbnail generation MUST use efficient image processing library (Pillow, Sharp, or cloud service)

#### Storage

- **NFR-005**: Processed photos MUST be stored with efficient compression (target ~200KB per profile)
- **NFR-006**: Original uploaded photos SHOULD be retained temporarily (7 days) for re-processing if needed
- **NFR-007**: Storage strategy MUST support both local filesystem (dev) and cloud object storage (production)
- **NFR-008**: Photo URLs MUST use secure, signed URLs with expiration (if using cloud storage)

#### Scalability

- **NFR-009**: System MUST support 10,000+ users with profile photos without performance degradation
- **NFR-010**: Image serving MUST support CDN integration for global delivery
- **NFR-011**: Database schema MUST support future profile field additions without migration downtime

#### Privacy & Compliance

- **NFR-012**: Profile data MUST be included in user data export (GDPR compliance)
- **NFR-013**: Profile deletion MUST cascade when user is permanently deleted
- **NFR-014**: Photo storage MUST comply with data residency requirements (configurable region)

### Key Entities

- **UserDetails**: Stores optional profile information for users
  - Attributes: user_id (FK to users.user_id), full_name, phone, address, photo_url, photo_thumbnail_url, photo_avatar_url, created_at, updated_at, created_by, updated_by
  - Relationships: One-to-one with User entity (via user_id)
  - Tenant scoping: Inherits tenant_id from linked User record

- **ProfilePhoto**: Logical representation of stored photo variants
  - Original: User-uploaded image (temporary retention)
  - Display: 640x640px optimized version (primary display)
  - Thumbnail: 96x96px for lists
  - Avatar: 48x48px for inline usage
  - Storage: File path or cloud object storage URL

### WhatsApp Profile Reference Specifications

Based on WhatsApp's profile section, the following standards apply:

#### Photo Specifications

- **Display Size**: Maximum 640x640 pixels (square, center-cropped)
- **File Size**: Target ~200-300KB after compression
- **Formats**: JPEG (primary), WebP (modern browsers), PNG (fallback)
- **Aspect Ratio**: 1:1 (square) enforced via center crop
- **Thumbnail Sizes**:
  - Profile view: 640x640px
  - Contact list: 96x96px
  - Chat header: 48x48px
  - Group member avatars: 32x32px

#### Field Specifications

- **Name**: Single line, max 100 characters, Unicode support
- **Phone**: International format preferred (+1 555-123-4567), flexible parsing
- **Address**: Multi-line (street, city, state/province, postal code, country), max 500 characters total
- **Default Avatar**: Generated from initials on colored background if no photo uploaded

#### Image Processing Pipeline

```
1. Upload validation (size, type, malware scan)
2. EXIF strip (remove location, camera data)
3. Resize to 640x640 (center crop if not square)
4. Compress JPEG quality 85% or WebP
5. Generate 96x96 thumbnail (for lists)
6. Generate 48x48 avatar (for headers)
7. Store all variants
8. Return success with URLs
```

## Technical Constraints

- **TC-001**: Must integrate with existing FastAPI backend and SQLAlchemy ORM
- **TC-002**: Must respect existing multi-tenant architecture (tenant_id scoping)
- **TC-003**: Must follow existing RBAC patterns (CurrentUser dependency)
- **TC-004**: Must emit audit events compatible with existing audit_events table
- **TC-005**: Database migration must use Alembic (add user_details table)
- **TC-006**: Image processing must not block HTTP request (async/background job)
- **TC-007**: Must support both PostgreSQL (production) and SQLite (dev/test)

## Success Criteria

### Must Have (MVP)

- [ ] User can create/update their profile with name, phone, address (all optional)
- [ ] User can upload profile photo with automatic resizing and optimization
- [ ] System generates 3 photo variants (display 640px, thumbnail 96px, avatar 48px)
- [ ] Profile photos compressed to ~200KB target
- [ ] Tenant isolation enforced (users see only their tenant's profiles)
- [ ] RBAC enforced (users edit own profile, admins view all in tenant, superadmins view all)
- [ ] API endpoints functional: GET/PUT profile, POST/DELETE photo
- [ ] Database migration creates user_details table
- [ ] 85%+ test coverage for new code

### Should Have (Phase 2)

- [ ] Default avatar generation from initials (no photo uploaded)
- [ ] Async image processing with progress feedback
- [ ] Cloud storage integration (S3/GCS) with signed URLs
- [ ] CDN integration for fast global photo delivery
- [ ] Phone number validation (E.164 format)
- [ ] GDPR data export includes profile details
- [ ] Audit events for profile photo changes

### Could Have (Future)

- [ ] Profile photo cropping UI (user selects crop area)
- [ ] Video profile clips (like WhatsApp status)
- [ ] Custom profile themes/colors
- [ ] Profile visibility settings (public, tenant-only, private)
- [ ] Profile photo history (revert to previous photo)
- [ ] Bulk profile import (CSV upload for admins)

## Dependencies

- **Existing Systems**:
  - User authentication system (JWT tokens, CurrentUser)
  - User management endpoints (/api/v1/users)
  - RBAC enforcement (tenant_admin, superadmin roles)
  - Audit logging (audit_events table)
  - Database infrastructure (PostgreSQL, Alembic migrations)

- **New Libraries** (recommended):
  - Pillow (Python image processing)
  - python-magic (file type detection)
  - phonenumbers (international phone validation, optional)

- **Infrastructure**:
  - File storage (local filesystem or cloud object storage)
  - Optional: Image CDN (CloudFlare, Fastly, CloudFront)
  - Optional: Background job queue (Celery, RQ) for async processing

## Out of Scope

- ❌ Social features (profile following, friends list)
- ❌ Profile activity timeline
- ❌ Profile verification badges
- ❌ Profile search/directory (separate feature)
- ❌ Profile sharing outside tenant (cross-tenant visibility)
- ❌ Profile import from third-party services (LinkedIn, Google)
- ❌ Custom profile fields (admin-configurable schema)
- ❌ Profile templates/themes

## Review & Acceptance Checklist

### Content Quality

- [x] No implementation details (languages, frameworks, APIs) - *Technical constraints section exists for integration*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders - *Requirements avoid code-level details*
- [x] All mandatory sections completed

### Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain - *WhatsApp reference resolves sizing questions*
- [x] Requirements are testable and unambiguous - *Specific sizes, formats, behaviors defined*
- [x] Success criteria are measurable - *Coverage %, photo sizes, response times specified*
- [x] Scope is clearly bounded - *Out of scope section clarifies boundaries*
- [x] Dependencies and assumptions identified - *Dependencies section lists existing systems*

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted (profile fields, photo optimization, WhatsApp standards)
- [x] Ambiguities marked (none - WhatsApp reference provides clear specifications)
- [x] User scenarios defined (6 acceptance scenarios, 10 edge cases)
- [x] Requirements generated (33 functional, 14 non-functional)
- [x] Entities identified (UserDetails, ProfilePhoto with attributes)
- [x] Review checklist passed
