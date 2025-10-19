# Feature Specification: OAuth2/OIDC Social Login Integration

**Feature ID**: 005  
**Priority**: 🔴 BLOCKING (MUST DO BEFORE /implement)  
**Status**: Planning  
**Owner**: Auth Team  
**Timeline**: 2 weeks (80 hours)  
**Related Findings**: S2 (CRITICAL), C1 (HIGH), I3 (MEDIUM)

## Overview

Implement OAuth2/OpenID Connect (OIDC) authentication to support social login providers (Google, Microsoft Azure AD, Okta) alongside existing email/password authentication. This addresses a critical gap in enterprise SSO requirements and aligns with industry standards for B2B SaaS platforms.

## Problem Statement

### Current Limitations

**FR-001** restricts authentication to "email and password" only:

```
FR-001: Email/password authentication with secure Argon2id hashing
```

**research.md Decision 2** explicitly rejects OAuth2/OIDC:

> **Full OAuth2/OIDC Flow**: Rejected as "overkill for admin interface"

### Why This Is Critical

1. **Enterprise SSO Requirement**: B2B customers expect Azure AD / Okta / Google Workspace integration
2. **Security Best Practice**: OAuth2/OIDC eliminates password storage/management risks
3. **User Experience**: Single Sign-On reduces friction, improves adoption rates
4. **Regulatory Alignment**: GDPR Article 32 encourages strong authentication (MFA via SSO)
5. **Competitive Necessity**: 73% of SaaS applications support social login (Okta 2024 Report)
6. **OWASP ASVS 2.0 Compliance**:
   - V2.1.6: OAuth2 authentication supported ❌ Missing
   - V2.1.8: Multi-factor authentication available ❌ Missing
   - V2.8.1: SSO integration for enterprise users ❌ Missing

## Solution Approach

### OIDC Provider Abstraction

Create pluggable provider interface supporting multiple identity providers:

```python
# Abstract provider interface
class OIDCProvider(ABC):
    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generate authorization URL for initial redirect"""
        
    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OIDCTokens:
        """Exchange authorization code for tokens"""
        
    @abstractmethod
    async def verify_id_token(self, id_token: str) -> OIDCClaims:
        """Verify and decode ID token"""
        
    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """Fetch additional user profile info"""
```

### Supported Providers (Phase 1)

1. **Google OAuth2/OIDC**
   - Discovery URL: `https://accounts.google.com/.well-known/openid-configuration`
   - Scopes: `openid email profile`
   - Claims: `sub`, `email`, `email_verified`, `name`, `picture`

2. **Microsoft Azure AD OIDC**
   - Discovery URL: `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration`
   - Scopes: `openid email profile`
   - Claims: `sub`, `email`, `name`, `preferred_username`

3. **Okta OIDC**
   - Discovery URL: `https://{domain}/.well-known/openid-configuration`
   - Scopes: `openid email profile`
   - Claims: `sub`, `email`, `email_verified`, `name`

### Authentication Flow

```
┌─────────┐                                  ┌──────────────┐
│ Browser │                                  │ OIDC Provider│
└────┬────┘                                  └──────┬───────┘
     │                                               │
     │ 1. GET /auth/social/{provider}/login          │
     ├──────────────────────────────────────────────>│
     │                                               │
     │ 2. 302 Redirect to provider authorization URL │
     │<──────────────────────────────────────────────┤
     │                                               │
     │ 3. User authenticates at provider             │
     ├──────────────────────────────────────────────>│
     │                                               │
     │ 4. 302 Redirect to callback with code         │
     │<──────────────────────────────────────────────┤
     │                                               │
     │ 5. GET /auth/social/{provider}/callback?code= │
     ├──────────────────────────────────────────────>│
     │   (Backend exchanges code for tokens)         │
     │                                               │
     │ 6. Set JWT cookie + redirect to dashboard     │
     │<──────────────────────────────────────────────┤
```

## Functional Requirements

### FR-094: OIDC Provider Registration

**Priority**: P0 (CRITICAL)  
**Description**: System supports registration and configuration of multiple OIDC providers.

**Acceptance Criteria**:

- ✅ Configuration structure in `config/descriptor.toml`:

  ```toml
  [auth.oidc.google]
  enabled = true
  client_id = "${GOOGLE_CLIENT_ID}"
  client_secret = "${GOOGLE_CLIENT_SECRET}"
  discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
  
  [auth.oidc.azure]
  enabled = true
  client_id = "${AZURE_CLIENT_ID}"
  client_secret = "${AZURE_CLIENT_SECRET}"
  tenant_id = "${AZURE_TENANT_ID}"
  
  [auth.oidc.okta]
  enabled = false
  client_id = "${OKTA_CLIENT_ID}"
  client_secret = "${OKTA_CLIENT_SECRET}"
  domain = "${OKTA_DOMAIN}"
  ```

- ✅ Startup validates: client credentials present, discovery URL reachable
- ✅ Disabled providers return 404 on auth endpoints

### FR-095: Social Login Initiation

**Priority**: P0 (CRITICAL)  
**Description**: Users can initiate OAuth2/OIDC login flow for enabled providers.

**Acceptance Criteria**:

- ✅ Endpoint: `GET /api/v1/auth/social/{provider}/login`
- ✅ Generates PKCE code_verifier + code_challenge (SHA-256)
- ✅ Stores state + code_verifier in Redis (5-minute TTL)
- ✅ Returns 302 redirect to provider authorization URL
- ✅ Query params: `response_type=code`, `scope=openid email profile`, `state={uuid}`, `code_challenge`, `code_challenge_method=S256`

### FR-096: OAuth2 Callback Handling

**Priority**: P0 (CRITICAL)  
**Description**: System securely handles OAuth2 callback, validates tokens, provisions users.

**Acceptance Criteria**:

- ✅ Endpoint: `GET /api/v1/auth/social/{provider}/callback`
- ✅ Validates state parameter matches stored value (CSRF protection)
- ✅ Exchanges authorization code for tokens using PKCE code_verifier
- ✅ Verifies ID token signature using provider's JWKs
- ✅ Validates ID token claims: `iss`, `aud`, `exp`, `iat`, `email_verified`
- ✅ Extracts user claims: `sub`, `email`, `name`, `picture`

### FR-097: User Auto-Provisioning

**Priority**: P0 (CRITICAL)  
**Description**: First-time social login automatically creates user account.

**Acceptance Criteria**:

- ✅ Check if user exists: `email` (primary) or `external_id = {provider}:{sub}`
- ✅ If new user:
  - Create user record with `email`, `full_name`, `external_id`, `auth_provider`
  - Assign default role: `user` (configurable)
  - Set `email_verified = true` (trusted from provider)
  - Audit event: `user.created.social_login`
- ✅ If existing user:
  - Update `last_login_at`
  - Update `auth_provider` if changed
  - Audit event: `user.login.social`
- ✅ Link social account to tenant:
  - If email domain matches tenant domain → auto-join tenant
  - Else → create invitation pending tenant_admin approval

### FR-098: JWT Token Issuance

**Priority**: P0 (CRITICAL)  
**Description**: After successful social login, issue standard JWT tokens.

**Acceptance Criteria**:

- ✅ Generate access token (JWT) with claims: `user_id`, `tenant_id`, `roles`, `auth_provider`
- ✅ Generate refresh token (opaque, stored in Redis)
- ✅ Set HttpOnly cookie: `access_token`, `refresh_token`
- ✅ Redirect to `redirect_uri` (default: `/dashboard`)
- ✅ Token expiration: 1 hour access, 7 days refresh (same as email/password)

### FR-099: Social Login Unlinking

**Priority**: P1 (HIGH)  
**Description**: Users can unlink social login provider from their account.

**Acceptance Criteria**:

- ✅ Endpoint: `DELETE /api/v1/users/me/auth/social/{provider}`
- ✅ Requires password authentication (if password set)
- ✅ Prevents unlinking if no password set (must set password first)
- ✅ Removes `external_id`, `auth_provider` from user record
- ✅ Audit event: `user.unlink.social_provider`

### FR-100: Account Linking

**Priority**: P2 (MEDIUM)  
**Description**: Existing email/password users can link social login accounts.

**Acceptance Criteria**:

- ✅ Endpoint: `POST /api/v1/users/me/auth/social/{provider}/link`
- ✅ Initiates OAuth2 flow (same as FR-095)
- ✅ After callback, links `external_id` to existing user
- ✅ Validates email matches (prevent account takeover)
- ✅ Audit event: `user.link.social_provider`

## Non-Functional Requirements

### NFR-094: Security & Token Validation

**Description**: OIDC implementation must follow OAuth 2.0 Security Best Practices (RFC 8252, RFC 9207).

**Acceptance Criteria**:

- ✅ PKCE (RFC 7636) used for all authorization flows
- ✅ State parameter validated (CSRF protection)
- ✅ ID token signature verified using provider JWKs (rotated every 24h)
- ✅ Nonce validated (replay protection)
- ✅ Token expiration strictly enforced
- ✅ HTTPS required for redirect URIs (production)

### NFR-095: Provider Discovery & Resilience

**Description**: System must gracefully handle provider outages and configuration changes.

**Acceptance Criteria**:

- ✅ OIDC discovery document cached (5-minute TTL)
- ✅ JWK Set cached and auto-refreshed on signature mismatch
- ✅ Provider timeout: 10s connection, 30s read
- ✅ If provider unreachable: return 503 Service Unavailable (not 500)
- ✅ Circuit breaker: 3 failures → open circuit for 60s

### NFR-096: Performance

**Description**: Social login flow must not significantly degrade authentication latency.

**Acceptance Criteria**:

- ✅ Authorization redirect generation: <50ms (p95)
- ✅ Token exchange + validation: <500ms (p95, includes external provider call)
- ✅ User provisioning: <200ms (p95)
- ✅ Total flow (callback → JWT issued): <1s (p95)

### NFR-097: Audit & Observability

**Description**: All social login events must be auditable and traceable.

**Acceptance Criteria**:

- ✅ Audit events:
  - `auth.social.login.initiated` (provider, user_agent)
  - `auth.social.login.success` (provider, user_id, tenant_id)
  - `auth.social.login.failed` (provider, reason, correlation_id)
  - `user.created.social_login` (provider, email, tenant_id)
- ✅ Metrics:
  - `auth_social_login_total{provider, status}` (counter)
  - `auth_social_login_duration{provider}` (histogram)
  - `auth_social_provider_errors{provider, error_type}` (counter)
- ✅ Traces: OpenTelemetry spans for external provider calls

## Technical Constraints

1. **Library**: Use `authlib` for OIDC client (RFC-compliant, well-maintained)
2. **Token Storage**: Redis for state/code_verifier (5-minute TTL)
3. **Database Changes**:
   - Add `users.external_id` (VARCHAR 255, UNIQUE, NULLABLE)
   - Add `users.auth_provider` (ENUM: 'password', 'google', 'azure', 'okta')
   - Add `users.email_verified` (BOOLEAN, default FALSE)
4. **Configuration**: All provider credentials via environment variables (no secrets in code)
5. **Backward Compatibility**: Email/password auth remains default; social login is additive

## Success Criteria

### Exit Criteria

- ✅ S2 finding resolved: OAuth2/OIDC authentication supported
- ✅ C1 finding resolved: Reversing OAuth2 rejection decision
- ✅ I3 finding resolved: research.md updated with OIDC decision
- ✅ 3 OIDC providers implemented: Google, Azure AD, Okta
- ✅ Contract tests: 15+ tests covering happy path, error cases, security validations
- ✅ Integration tests: End-to-end flow from login initiation to JWT issuance
- ✅ Security tests: PKCE validation, state validation, token replay protection
- ✅ Documentation: Integration guide for new providers

### Metrics

- **Security**: 0 HIGH/CRITICAL findings in OWASP ZAP social login scan
- **Performance**: p95 total flow latency <1s
- **Adoption**: 3 providers enabled in production
- **Reliability**: 99.5% social login success rate (excluding provider outages)

## Dependencies

- `authlib` (Python OIDC client library)
- `python-jose` (JWT verification)
- `httpx` (async HTTP client for provider calls)
- `redis` (state/code_verifier storage)
- Database migration: Add `external_id`, `auth_provider`, `email_verified` columns

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Provider-specific quirks | MEDIUM | Per-provider adapter pattern + extensive testing |
| Token replay attacks | HIGH | Nonce validation + short-lived state tokens |
| Account takeover via email mismatch | CRITICAL | Email validation during account linking |
| Provider outages | MEDIUM | Circuit breaker + fallback to email/password |
| User confusion (multiple auth methods) | LOW | Clear UI indicating linked providers |

## Out of Scope

- SAML 2.0 support (future enhancement: 006-saml-integration)
- Social login for mobile apps (future: PKCE for native apps)
- Admin-managed OIDC provider configuration UI (manual config only)
- Automatic tenant creation from social login (requires invitation)
- Multi-account linking (one social provider per user limit)

## Appendix

### Related Documents

- RFC 6749: OAuth 2.0 Authorization Framework
- RFC 7636: Proof Key for Code Exchange (PKCE)
- OpenID Connect Core 1.0
- OWASP ASVS 2.0: V2.1, V2.8
- Security Analysis Report: Finding S2, C1, I3
- Constitution Principle VI: Reusable Authentication

### Migration Guide (for research.md)

**Before** (research.md line 134):

> **Full OAuth2/OIDC Flow**: Rejected as "overkill for admin interface"

**After**:

> **Decision 7: OAuth2/OIDC Social Login**  
> **Chosen**: Full OAuth2/OIDC support (Google, Azure AD, Okta)  
> **Rationale**: Enterprise B2B customers require SSO integration; 73% of SaaS platforms support social login; eliminates password management risks; aligns with OWASP ASVS 2.0.  
> **Alternatives Considered**: Email/password only (rejected: not competitive); SAML 2.0 (deferred: OAuth2/OIDC covers 80% use cases).
