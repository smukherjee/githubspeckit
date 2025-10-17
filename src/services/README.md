# Services Module

## Purpose

The `services/` module contains **application services** (also called "use cases" in hexagonal architecture) that orchestrate domain logic and coordinate between domain entities, repositories, and external adapters.

## Architecture Decision

Services sit **between the API layer and the domain layer** in a hexagonal architecture:

```
API Layer (FastAPI routes)
    ↓
Service Layer (application services)
    ↓
Domain Layer (entities, value objects, domain services)
    ↓
Repository Ports (interfaces)
    ↑
Adapter Layer (repository implementations)
```

### Why Not in `domain/`?

Services are **application-specific orchestration logic**, not pure domain logic:

1. **Domain Layer**: Pure business rules, entities, and domain services (e.g., `TenantService`, `UserService`)
   - No knowledge of persistence, HTTP, or infrastructure
   - Focused on business invariants and domain rules

2. **Service Layer**: Application use cases (e.g., "register new user", "update tenant settings")
   - Coordinates multiple domain entities
   - Uses repository ports (defined in domain, implemented in adapters)
   - May handle transactions, validation, and orchestration

### Constitution Compliance (v1.5.1)

**Principle I (Modularity)**: ✅ Services are a distinct layer in the hexagonal architecture

**Principle II (Hexagonal Architecture)**: ✅ Services orchestrate domain logic without being domain logic themselves

**Dependency Flow**: 
- ✅ Services depend on domain (inward)
- ✅ Services do NOT depend on adapters (uses ports instead)
- ✅ API layer depends on services (inward)

## Module Structure

```
src/services/
├── __init__.py              # Public API exports
├── tenant_service.py        # Tenant management use cases
├── user_service.py          # User management use cases
├── auth_service.py          # Authentication use cases
└── policy_service.py        # Policy evaluation use cases
```

## Usage Example

```python
from services.user_service import UserService
from domain.users.repository import UserRepository

# In API route
@router.post("/users")
async def create_user(
    user_data: UserCreate,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    # Service orchestrates domain logic + persistence
    user = await user_service.register_user(
        tenant_id=user_data.tenant_id,
        email=user_data.email,
        password=user_data.password,
        repository=user_repo
    )
    return UserResponse.from_domain(user)
```

## Service Responsibilities

1. **Orchestration**: Coordinate multiple domain entities/repositories
2. **Validation**: Application-level validation (beyond domain invariants)
3. **Transaction Management**: Ensure atomic operations across repositories
4. **Error Handling**: Convert domain exceptions to application errors

## Related Documentation

- Constitution v1.5.1, Principle II (Hexagonal Architecture)
- Domain-Driven Design: Application Services pattern
- Hexagonal Architecture: Use Cases layer
