# ADR-004: Disable Rate Limiting for V1.0 Intranet Deployment

**Status**: Accepted  
**Date**: 2025-10-20  
**Deciders**: Engineering Team  
**Related**: FR-046 to FR-054 (Rate Limiting Requirements)

## Context

The application was originally designed with IP-based rate limiting using slowapi (FastAPI port of Flask-Limiter) and Redis for distributed rate limiting across multiple instances. The rate limiting implementation included:

- Fixed-window rate limiting per IP address
- Configurable limits via `RATE_LIMIT_USER_CREATION` (default: 100 requests/hour)
- Redis backend for horizontal scaling
- Superadmin bypass mechanism (attempted but incomplete due to slowapi limitations)

### Technical Issues Encountered

1. **slowapi exempt_when limitation**: The `exempt_when` parameter expects a no-argument callable, but accessing request context (needed to check user roles) requires the `Request` object. Attempted workarounds with ContextVars had timing issues.

2. **Test interference**: In-memory rate limiting state persists across test cases within the same pytest session, causing test failures due to accumulated rate limit hits.

3. **Added complexity**: Rate limiting added dependencies (slowapi, Redis), configuration overhead, and debugging complexity for minimal benefit in the target deployment environment.

## Decision

**Disable all rate limiting functionality for V1.0 release.**

Rationale:
- **Deployment Environment**: V1.0 will be deployed in a private intranet environment with trusted users and controlled access
- **Limited Attack Surface**: Intranet deployment significantly reduces risk of abuse that rate limiting protects against
- **Simplification**: Removes technical debt from incomplete superadmin bypass implementation
- **Test Reliability**: Eliminates test failures caused by rate limiting state management
- **Future Ready**: Code remains in codebase (commented out) for easy re-enablement when deploying to public-facing environments

## Implementation

### Files Modified

1. **src/adapters/api/app.py**
   - Commented out `limiter`, `_rate_limit_exceeded_handler`, and `RateLimitExceeded` imports
   - Commented out rate limiting initialization in `create_app()`
   - Added ADR-004 reference comments

2. **src/adapters/api/routers/users.py**
   - Commented out rate limiting imports
   - Commented out `@limiter.limit()` decorator on `create_user` endpoint
   - Commented out rate limit configuration loading
   - Updated docstring to note rate limiting is disabled
   - Added ADR-004 reference comments

### Code Preservation

All rate limiting code is preserved as comments rather than deleted to:
- Document the original implementation approach
- Enable easy re-enablement for future deployments
- Maintain architectural understanding

### Dependencies Retained

The following dependencies remain in `requirements.txt` but are not actively used:
- `slowapi` - Rate limiting library
- Redis connection configuration (also used for session storage)

## Consequences

### Positive

✅ **Simplified deployment**: No Redis dependency required for rate limiting  
✅ **Improved test reliability**: No rate limit state interference between tests  
✅ **Reduced complexity**: One less feature to debug and maintain in V1.0  
✅ **Appropriate for context**: Matches security needs of intranet deployment  
✅ **Future flexibility**: Easy to re-enable when needed  

### Negative

⚠️ **No protection against abuse**: Malicious or buggy clients can flood endpoints  
⚠️ **No DoS protection**: No built-in throttling for resource-intensive operations  
⚠️ **Manual monitoring required**: Operators must monitor for abnormal usage patterns  

### Mitigation Strategies

For V1.0 intranet deployment:
1. **Network-level controls**: Rely on firewall and network access controls
2. **Audit logging**: Monitor audit logs for unusual activity patterns
3. **User accountability**: Intranet users are identifiable and accountable
4. **Incremental rollout**: Deploy to small user base initially
5. **Observability**: Use metrics and alerts to detect anomalous behavior

For future public deployments:
1. **Uncomment rate limiting code** in app.py and users.py
2. **Fix superadmin bypass**: Implement middleware-based ContextVar approach or custom decorator
3. **Test thoroughly**: Ensure rate limiting doesn't interfere with legitimate usage
4. **Configure appropriately**: Adjust limits based on expected traffic patterns

## Alternatives Considered

### Alternative 1: Fix slowapi exempt_when
- **Approach**: Implement middleware to set ContextVar before rate limiter runs
- **Rejected**: Complex timing issues; over-engineering for intranet deployment

### Alternative 2: Custom rate limiting decorator
- **Approach**: Build custom rate limiting with proper request context access
- **Rejected**: Significant development effort; not justified for V1.0 scope

### Alternative 3: Accept superadmin rate limiting
- **Approach**: Keep rate limiting but remove exempt_when bypass
- **Rejected**: Still adds complexity without proportional benefit for intranet use

### Alternative 4: Use application-level throttling
- **Approach**: Implement throttling in business logic rather than HTTP middleware
- **Rejected**: More invasive changes; harder to configure and monitor

## References

- [slowapi documentation](https://github.com/laurentS/slowapi)
- [Flask-Limiter exempt_when](https://flask-limiter.readthedocs.io/en/stable/#exempt-routes)
- FR-046 to FR-054: Original rate limiting requirements
- Phase 3.6 Tasks (T048-T054): Rate limiting implementation tasks
- Test failures: `test_rate_limit_headers_present_in_responses` and related

## Review and Update

This decision should be reviewed when:
- Application is deployed to public-facing environment
- Security audit identifies rate limiting as required control
- Usage patterns indicate need for throttling
- V2.0 planning begins

**Next Review Date**: Before public deployment or 2026-Q2, whichever comes first
