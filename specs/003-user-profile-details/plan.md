# Implementation Plan: User Profile Details

**Branch**: `003-user-profile-details` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/Users/sujoymukherjee/code/githubspeckit/specs/003-user-profile-details/spec.md`

## Summary

Add a new `user_details` table to store optional user profile information (full name, profile photo, phone, address). Implement photo upload with automatic resizing/optimization following WhatsApp profile standards (640x640px display, 96x96px thumbnail, 48x48px avatar, ~200KB compressed). Provide REST API endpoints for profile CRUD operations with tenant isolation and RBAC enforcement. All fields optional, tenant-scoped, with audit trail.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI 0.115.6, SQLAlchemy 2.0.36 (async), Pillow 11.0.0 (image processing), python-magic 0.4.27 (file type detection)  
**Storage**: PostgreSQL (production), SQLite (dev/test); image storage: local filesystem (dev), S3-compatible object storage (production)  
**Testing**: pytest 8.4.2 with pytest-asyncio, httpx (API testing), pytest-cov (coverage)  
**Target Platform**: Linux server (Docker/Kubernetes deployment)  
**Project Type**: Backend API (existing multi-tenant FastAPI application)  
**Performance Goals**: Profile photo upload/processing <5s p95, profile retrieval <200ms p95, image serving <100ms p50  
**Constraints**: Max 10MB upload size, ~200KB compressed photo target, tenant isolation enforced, RBAC required  
**Scale/Scope**: 10,000+ users with photos, 3 photo variants per user (display, thumbnail, avatar), async background processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluate and explicitly confirm (checklist) before proceeding:

- [x] **Architecture**: Domain layer (`domain/users/`) free of framework/infrastructure imports ✅  
  *UserDetails domain model will be pure Python dataclass, no FastAPI/SQLAlchemy in domain*

- [x] **Test-First & Coverage**: Planned failing tests exist AND projected coverage meets thresholds (≥90% domain, ≥85% overall; 100% critical auth/tenancy paths) ✅  
  *Contract tests for photo upload, unit tests for UserDetails model, integration tests for RBAC, >90% coverage target*

- [x] **Multi-Tenancy**: Every new data access path includes tenant context + filtering ✅  
  *user_details inherits tenant_id from users table; all queries scoped by tenant_id via CurrentUser*

- [x] **RBAC & Policies**: Authorization expressed via registered policies—no inline role branching ✅  
  *Users can edit own profile, tenant_admin view-only for tenant, superadmin view-only for all tenants*

- [x] **Auth Reuse**: No domain-specific logic added inside auth core; only registrations/extensions ✅  
  *Uses existing CurrentUser dependency, no auth_core modifications needed*

- [x] **Switchable Persistence**: Repositories stay interface-driven; no leakage of ORM/session into domain ✅  
  *UserDetailsRepository interface with SQLAlchemy implementation, domain models isolated*

- [x] **Observability**: Planned metrics, centrally configurable structured logs (export + redaction), tracing spans for each new boundary ✅  
  *Metrics: photo_upload_duration, photo_processing_duration, profile_update_count; logs for photo upload start/complete/error; PII redaction for address fields*

- [x] **API Versioning**: New/changed endpoints supply version impact assessment ✅  
  *New endpoints under /api/v1/users/{user_id}/profile, backward compatible (no breaking changes)*

- [x] **Performance Budgets**: Declared baseline p95/p99 expectations ✅  
  *Photo upload <5s p95, profile retrieval <200ms p95, image processing async (background job)*

- [x] **Unified Configuration**: Single descriptor (no direct env access) + DEPLOY_MODE implications addressed ✅  
  *Photo storage path configurable via PHOTO_STORAGE_PATH, PHOTO_STORAGE_TYPE (local|s3), max upload size via MAX_UPLOAD_SIZE_MB*

- [x] **Developer Experience & Embed**: Minimal local infra (fallback mocks) + embed session/cookie strategy documented ✅  
  *Local dev uses filesystem storage; production uses S3-compatible; seed script includes sample user_details*

- [x] **Complexity**: Any new adapter/infra addition justified vs simpler alternative ✅  
  *Image processing adapter needed for Pillow, justified by photo optimization requirements; no new databases/queues initially*

- [x] **Security Testing**: OWASP Top 10 mapping updates + dynamic/pen test considerations documented ✅  
  *File upload vulnerability tests (malicious files, oversized, executable), XSS in address/name fields, tenant isolation breach attempts*

- [x] **Code Quality & Simplicity**: DRY/KISS/YAGNI respected; no premature abstractions; duplication/complexity impact considered ✅  
  *Reuse existing auth/RBAC patterns, simple domain model, no complex state machines, photo processing extracted to utility*

**Initial Constitution Check**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/003-user-profile-details/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Database schema & entities
├── quickstart.md        # Phase 1: Integration scenario
├── contracts/           # Phase 1: OpenAPI fragments
│   ├── openapi-user-profile.yaml
│   └── openapi-photo-upload.yaml
└── tasks.md             # Phase 2: Generated by /tasks command
```

### Source Code (repository root)

```text
src/
├── domain/
│   └── users/
│       ├── models.py                    # User, UserDetails dataclasses
│       └── repositories.py              # UserDetailsRepository interface
├── adapters/
│   ├── api/
│   │   └── routers/
│   │       ├── users.py                 # Extended with profile endpoints
│   │       └── profile.py               # New: profile-specific routes
│   ├── persistence/
│   │   └── repositories.py              # SQLAlchemyUserDetailsRepository
│   └── media/
│       ├── photo_processor.py           # New: Image resizing/optimization
│       └── storage.py                   # New: File storage abstraction (local/S3)
├── schemas/
│   └── user_profile.py                  # New: Pydantic models for API
└── services/
    └── profile_service.py               # New: Business logic for profile operations

alembic/
└── versions/
    └── 20251017_xxxx_add_user_details_table.py  # New migration

tests/
├── contract/
│   └── test_user_profile_api.py         # New: OpenAPI contract tests
├── integration/
│   ├── test_profile_management.py       # New: Profile CRUD tests
│   └── test_photo_upload.py             # New: Photo upload integration tests
└── unit/
    ├── domain/
    │   └── test_user_details_model.py   # New: Domain model tests
    └── adapters/
        ├── test_photo_processor.py      # New: Image processing tests
        └── test_profile_repository.py   # New: Repository tests

scripts/
└── seed_infysight.py                    # Extended: Add sample user_details

config/
└── descriptor.toml                      # Extended: Photo storage config
```

**Structure Decision**: Extending existing FastAPI backend monorepo. New user_details domain entity under `src/domain/users/`, new profile router under `src/adapters/api/routers/`, new media adapter layer for photo processing. Database migration via Alembic. Follows hexagonal architecture pattern established in project.

## Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - ✅ Image processing library choice (Pillow vs alternatives)
   - ✅ Photo storage strategy (filesystem vs object storage vs database BLOB)
   - ✅ Async background processing approach (Celery vs inline vs FastAPI BackgroundTasks)
   - ✅ Image format optimization (JPEG vs WebP vs both)
   - ✅ WhatsApp photo specs interpretation (exact sizes, compression ratios)
   - ✅ Phone number validation library (phonenumbers vs regex)
   - ✅ Secure file upload patterns (malware scanning, EXIF stripping)

2. **Generate and dispatch research agents**:

    ```text
    Task 1: Research Python image processing libraries (Pillow vs pillow-simd vs opencv-python)
      → Compare performance, ease of use, production readiness

    Task 2: Research photo storage strategies for FastAPI
      → Local filesystem vs S3/MinIO vs database BLOB
      → Consider: scalability, CDN integration, cost, complexity

    Task 3: Research async background job patterns in FastAPI
      → FastAPI BackgroundTasks vs Celery vs RQ vs arq
      → Consider: complexity, observability, failure handling

    Task 4: Research image format optimization
      → JPEG quality levels vs WebP compression
      → Browser compatibility, file size, visual quality tradeoffs

    Task 5: Research WhatsApp profile photo specifications
      → Exact pixel dimensions, compression ratios, formats
      → Center-crop algorithm, aspect ratio handling

    Task 6: Research phone number validation libraries
      → phonenumbers (libphonenumber port) vs regex patterns
      → International format handling, validation depth

    Task 7: Research secure file upload best practices
      → OWASP file upload vulnerabilities
      → EXIF metadata stripping, magic byte validation, malware scanning
    ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all technology choices documented

## Phase 1: Design & Contracts

Prerequisites: research.md complete

1. **Extract entities from feature spec** → `data-model.md`:
   - **UserDetails**: user_id (FK), full_name, phone, address, photo_url, photo_thumbnail_url, photo_avatar_url, created_at, updated_at, created_by, updated_by
   - Relationships: One-to-one with User (via user_id)
   - Validation: name max 100 chars, phone max 20 chars, address max 500 chars
   - Indexes: user_id (PK), tenant isolation via JOIN with users table
   - State transitions: N/A (stateless CRUD)

2. **Generate API contracts** from functional requirements:
   - Endpoints:
     - `GET /api/v1/users/{user_id}/profile` → Retrieve profile details
     - `PUT /api/v1/users/{user_id}/profile` → Update profile details
     - `POST /api/v1/users/{user_id}/profile/photo` → Upload photo (multipart/form-data)
     - `DELETE /api/v1/users/{user_id}/profile/photo` → Remove photo
     - `GET /api/v1/users/me/profile` → Current user's profile (convenience)
   - Output OpenAPI fragments to `/contracts/`
     - `openapi-user-profile.yaml` (CRUD operations)
     - `openapi-photo-upload.yaml` (multipart upload spec)

3. **Generate contract tests** from contracts:
   - `tests/contract/test_user_profile_api.py`:
     - Test GET profile returns correct schema
     - Test PUT profile validates input
     - Test POST photo validates file type/size
     - Test DELETE photo returns 204
     - Test tenant isolation (401/403 responses)
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Story 1 → `test_user_updates_profile_details()` (integration test)
   - Story 2 → `test_user_uploads_profile_photo()` (integration test)
   - Story 3 → `test_admin_views_user_profiles()` (integration test)
   - Quickstart: Happy path walkthrough (create profile, upload photo, retrieve, update)

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
   - Add: Pillow for image processing, user_details table schema, profile endpoints
   - Update recent changes: "Added user profile details feature with photo upload"
   - Keep under 150 lines

**Output**: data-model.md, /contracts/openapi-user-profile.yaml, /contracts/openapi-photo-upload.yaml, failing tests, quickstart.md, .github/copilot-instructions.md

## Phase 2: Task Planning Approach

Description: This section describes what the /tasks command will do - DO NOT execute during /plan.

**Task Generation Strategy**:

1. **Setup Tasks** (Phase 3.1):
   - Install dependencies (Pillow, python-magic, phonenumbers)
   - Configure photo storage (env vars, directory structure)
   - Create Alembic migration for user_details table
   - Update seed script with sample profiles

2. **Contract Test Tasks** (Phase 3.2 - TDD):
   - Write contract tests for GET /profile (fails)
   - Write contract tests for PUT /profile (fails)
   - Write contract tests for POST /photo (fails)
   - Write contract tests for DELETE /photo (fails)
   - Write RBAC enforcement tests (fails)
   - Each contract test task marked [P] (parallel execution)

3. **Domain Layer Tasks** (Phase 3.3):
   - Create UserDetails dataclass in domain/users/models.py
   - Create UserDetailsRepository interface
   - Write unit tests for UserDetails model

4. **Adapter Layer Tasks** (Phase 3.4):
   - Implement SQLAlchemyUserDetailsRepository
   - Create photo_processor.py (resize, compress, thumbnail generation)
   - Create storage.py (filesystem and S3 implementations)
   - Write unit tests for photo processor
   - Write unit tests for storage adapters
   - Each adapter task marked [P]

5. **API Layer Tasks** (Phase 3.5):
   - Create Pydantic schemas in schemas/user_profile.py
   - Implement GET /users/{id}/profile endpoint
   - Implement PUT /users/{id}/profile endpoint
   - Implement POST /users/{id}/profile/photo endpoint
   - Implement DELETE /users/{id}/profile/photo endpoint
   - Add RBAC decorators/checks

6. **Integration Test Tasks** (Phase 3.6):
   - Write integration test for profile CRUD
   - Write integration test for photo upload workflow
   - Write integration test for tenant isolation
   - Write integration test for RBAC enforcement

7. **Polish Tasks** (Phase 3.7):
   - Add observability (metrics, logs, traces)
   - Add API documentation (OpenAPI descriptions)
   - Update quickstart.md with examples
   - Performance validation (photo processing <5s)
   - Security validation (file upload vulnerabilities)

**Ordering Strategy**:

- TDD strict: Contract tests → Domain → Adapters → API → Integration tests
- Dependencies: Migration → Domain models → Repositories → Services → Endpoints
- Parallelization: Different contract tests [P], different adapters [P], different unit test files [P]

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

Scope: These phases are beyond the scope of the /plan command.

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
  - Run migration: `alembic upgrade head`
  - Implement domain models (pure Python)
  - Implement repositories (SQLAlchemy)
  - Implement photo processor (Pillow)
  - Implement API endpoints (FastAPI)
  - Make tests pass (green phase)

**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)  
  - `pytest tests/contract/test_user_profile_api.py` → all pass
  - `pytest tests/integration/test_profile_management.py` → all pass
  - Coverage check: `pytest --cov=src/domain/users --cov=src/adapters/api/routers/profile --cov-report=term-missing` → ≥90%
  - Quickstart execution: Upload 5MB photo, verify <5s processing, verify 3 variants generated
  - Performance test: 100 concurrent profile uploads, p95 <5s
  - Security audit: Attempt malicious file upload, XSS in fields, tenant boundary breach

## Complexity Tracking

Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| None | N/A | N/A |

**Justification**: No constitutional violations. Feature extends existing architecture without new infrastructure components. Image processing adapter follows established adapter pattern. Photo storage abstraction enables future cloud migration without violating switchable infrastructure principle.

## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - 42 tasks generated)
- [x] Phase 3: Tasks generated (/tasks command)
- [~] Phase 4: Implementation IN PROGRESS (Setup complete: T001-T005 ✅, TDD tests next: T006-T015)
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS (data model, contracts, quickstart reviewed)
- [x] All NEEDS CLARIFICATION resolved (none existed, WhatsApp spec provided clarity)
- [x] Complexity deviations documented (none)

---

*Based on Constitution v1.5.1 - See `.specify/memory/constitution.md`*
