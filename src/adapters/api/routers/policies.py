
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from adapters.api.deps import get_db_session, get_audit_service, AuditService
from adapters.api.auth_deps import CurrentUser
from adapters.persistence.repositories import SQLAlchemyPolicyRepository
from domain.tenants.tenant_context import TenantContext
from domain.policy.models import Policy, PolicyRule, PolicyStatus, Decision

router = APIRouter(prefix="/v1/policies", tags=["policies"])

ALLOWED_RATIONALE_PREFIXES = {"role.allow", "policy.match", "tenant.scope"}


class DryRunRequest(BaseModel):
    tenant_id: str
    action: str
    resource_type: str
    attributes: Dict[str, Any] = {}


class DryRunResponse(BaseModel):
    decision: str
    rationales: List[str]
    model_config = ConfigDict()


class PolicyRegistrationRequest(BaseModel):
    policy_id: str
    version: int
    resource_type: str
    condition_expression: str
    effect: str  # ALLOW or DENY
    model_config = ConfigDict()


class PolicyResponse(BaseModel):
    id: str  # React-Admin requires 'id' field
    policy_id: str
    version: int
    resource_type: str
    condition_expression: str
    effect: str
    created_by: str | None = None
    created_at: str | None = None
    model_config = ConfigDict()


def _evaluate(action: str) -> tuple[str, List[str]]:
    # Extremely simplified evaluator stub.
    if action == "trigger_unknown":
        return "DENY", ["unknown.reason.code"]
    if action.startswith("read"):
        return "ALLOW", ["role.allow.reader", "tenant.scope.base"]
    return "ABSTAIN", ["policy.match.none"]


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run(
    req: DryRunRequest,
    session: AsyncSession = Depends(get_db_session)
) -> DryRunResponse:
    """Policy dry-run evaluation (Phase 3: database-backed, stub evaluator)."""
    decision, rationales = _evaluate(req.action)
    # Guard: any rationale not starting with allowed prefixes triggers error
    for r in rationales:
        if not any(r.startswith(p) for p in ALLOWED_RATIONALE_PREFIXES):
            raise HTTPException(status_code=400, detail="unknown_rationale_code")
    return DryRunResponse(decision=decision, rationales=rationales)


@router.post("/register", response_model=PolicyResponse, status_code=201)
async def register_policy(
    req: PolicyRegistrationRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> PolicyResponse:
    """Register policy with full storage (FR-062: Create policies).
    
    RBAC enforcement:
    - Superadmin: Can register policies
    - Tenant admin: Can register policies for their tenant
    - Regular users: Denied access
    """
    # RBAC check
    if "superadmin" not in current_user.roles and "tenant_admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to register policies")
    
    # Basic validation: effect value
    if req.effect not in {"ALLOW", "DENY"}:
        raise HTTPException(status_code=400, detail="invalid_effect")
    
    # Map string effect to Decision enum
    effect = Decision.allow if req.effect == "ALLOW" else Decision.deny
    
    # Create domain policy object
    policy_rule = PolicyRule(
        rule_id=f"{req.policy_id}_v{req.version}",
        version=req.version,
        resource=req.resource_type,
        action="*",  # Default to all actions
        effect=effect,
        condition={"expression": req.condition_expression}  # Store as structured data
    )
    
    policy = Policy(
        policy_id=req.policy_id,
        tenant_id=current_user.tenant_id,
        name=req.resource_type,
        rules=[policy_rule],
        status=PolicyStatus.active,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Persist using repository
    repo = SQLAlchemyPolicyRepository(session)
    saved_policy = await repo.upsert(policy)
    
    # Audit logging: Policy registration
    await audit_service.log(
        action_type="policy.register",
        tenant_id=current_user.tenant_id,
        metadata={
            "policy_id": saved_policy.policy_id,
            "resource_type": req.resource_type,
            "effect": req.effect,
            "version": req.version,
            "registered_by": current_user.user_id
        }
    )
    
    pol = PolicyResponse(
        id=saved_policy.policy_id,
        policy_id=saved_policy.policy_id,
        version=req.version,
        resource_type=req.resource_type,
        condition_expression=req.condition_expression,
        effect=req.effect,
        created_by=saved_policy.created_by,
        created_at=saved_policy.created_at.isoformat() if saved_policy.created_at else None,
    )
    return pol


def get_tenant_context(request: Request) -> TenantContext:
    """
    Extract tenant context from request state.
    
    Injected by TenantContextMiddleware in Phase 3.3.
    
    Args:
        request: FastAPI request object
    
    Returns:
        TenantContext from request.state
    
    Raises:
        HTTPException: 500 if tenant context not found (middleware not wired)
    """
    if not hasattr(request.state, "tenant_context"):
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "TENANT_CONTEXT_MISSING",
                    "message": "Tenant context not initialized (middleware not wired)",
                }
            },
        )
    return request.state.tenant_context


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    response: Response,
    request: Request,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    tenant_context: TenantContext = Depends(get_tenant_context),
    include_deleted: bool = False
) -> list[PolicyResponse]:
    """List policies with tenant isolation (FR-085/FR-087, FR-004 tenant security refactor).
    
    **V1.0 Behavior**: Tenant context extracted from JWT (or session for superadmin).
    Cross-tenant access requires superadmin session switching (POST /admin/context/tenant).
    
    **Authorization**: Middleware enforces tenant isolation
    
    RBAC enforcement:
    - Superadmin: Can list policies for any tenant (via session switching)
    - Tenant admin: Can only list policies for their own tenant
    - Regular users: Denied access
    """
    # RBAC check
    if "superadmin" not in current_user.roles and "tenant_admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to list policies")
    
    # Use effective_tenant_id from tenant context (handles superadmin session switching)
    target_tenant_id = str(tenant_context.effective_tenant_id)
    
    # Fetch from repository
    repo = SQLAlchemyPolicyRepository(session)
    policies = await repo.list_by_tenant(target_tenant_id, include_deleted=include_deleted)
    
    # Convert to response models
    policy_responses: list[PolicyResponse] = []
    for policy in policies:
        # Extract first rule for response (simplified)
        if policy.rules:
            first_rule = policy.rules[0]
            effect_str = "ALLOW" if first_rule.effect == Decision.allow else "DENY"
            condition_expr = first_rule.condition.get("expression", "") if first_rule.condition else ""
            
            policy_responses.append(PolicyResponse(
                id=policy.policy_id,
                policy_id=policy.policy_id,
                version=first_rule.version,
                resource_type=first_rule.resource,
                condition_expression=condition_expr,
                effect=effect_str,
                created_by=policy.created_by,
                created_at=policy.created_at.isoformat() if policy.created_at else None,
            ))
    
    # Add Content-Range header for React-Admin pagination
    total = len(policy_responses)
    response.headers["Content-Range"] = f"policies 0-{total-1 if total > 0 else 0}/{total}"
    
    return policy_responses


@router.put("/{policy_id}/disable", status_code=200)
async def disable_policy(
    policy_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> dict[str, str]:
    """Disable a policy (soft delete).
    
    RBAC enforcement:
    - Superadmin: Can disable any policy
    - Tenant admin: Can disable policies in their tenant only
    - Regular users: Denied access
    """
    # RBAC check
    if "superadmin" not in current_user.roles and "tenant_admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to disable policies")
    
    # Fetch policy
    repo = SQLAlchemyPolicyRepository(session)
    policy = await repo.get(policy_id)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Tenant isolation check
    if "superadmin" not in current_user.roles and policy.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot disable policy from another tenant")
    
    # Update status
    policy.status = PolicyStatus.disabled
    policy.updated_by = current_user.user_id
    policy.updated_at = datetime.now(timezone.utc)
    
    await repo.upsert(policy)
    
    # Audit logging
    await audit_service.log(
        action_type="policy.disable",
        tenant_id=policy.tenant_id,
        metadata={
            "policy_id": policy_id,
            "disabled_by": current_user.user_id
        }
    )
    
    return {"message": "Policy disabled successfully", "policy_id": policy_id}


@router.put("/{policy_id}/enable", status_code=200)
async def enable_policy(
    policy_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> dict[str, str]:
    """Enable a previously disabled policy.
    
    RBAC enforcement:
    - Superadmin: Can enable any policy
    - Tenant admin: Can enable policies in their tenant only
    - Regular users: Denied access
    """
    # RBAC check
    if "superadmin" not in current_user.roles and "tenant_admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to enable policies")
    
    # Fetch policy (include deleted to allow re-enabling)
    repo = SQLAlchemyPolicyRepository(session)
    policies = await repo.list_by_tenant(current_user.tenant_id, include_deleted=True)
    policy = next((p for p in policies if p.policy_id == policy_id), None)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Tenant isolation check
    if "superadmin" not in current_user.roles and policy.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot enable policy from another tenant")
    
    # Update status
    policy.status = PolicyStatus.active
    policy.updated_by = current_user.user_id
    policy.updated_at = datetime.now(timezone.utc)
    
    await repo.upsert(policy)
    
    # Audit logging
    await audit_service.log(
        action_type="policy.enable",
        tenant_id=policy.tenant_id,
        metadata={
            "policy_id": policy_id,
            "enabled_by": current_user.user_id
        }
    )
    
    return {"message": "Policy enabled successfully", "policy_id": policy_id}


@router.delete("/{policy_id}", status_code=200)
async def delete_policy(
    policy_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> dict[str, str]:
    """Delete a policy (soft delete by setting status to disabled).
    
    RBAC enforcement:
    - Superadmin: Can delete any policy
    - Tenant admin: Can delete policies in their tenant only
    - Regular users: Denied access
    """
    # RBAC check
    if "superadmin" not in current_user.roles and "tenant_admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete policies")
    
    # Fetch policy
    repo = SQLAlchemyPolicyRepository(session)
    policy = await repo.get(policy_id)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Tenant isolation check
    if "superadmin" not in current_user.roles and policy.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot delete policy from another tenant")
    
    # Soft delete: set status to disabled
    policy.status = PolicyStatus.disabled
    policy.updated_by = current_user.user_id
    policy.updated_at = datetime.now(timezone.utc)
    
    await repo.upsert(policy)
    
    # Audit logging
    await audit_service.log(
        action_type="policy.delete",
        tenant_id=policy.tenant_id,
        metadata={
            "policy_id": policy_id,
            "deleted_by": current_user.user_id
        }
    )
    
    return {"message": "Policy deleted successfully", "policy_id": policy_id}

__all__ = ["router"]