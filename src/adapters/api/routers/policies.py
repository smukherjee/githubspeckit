from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyPolicyRepository

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
    session: AsyncSession = Depends(get_db_session)
) -> PolicyResponse:
    """Register policy (Phase 3: database-backed stub)."""
    # Basic validation: effect value
    if req.effect not in {"ALLOW", "DENY"}:
        raise HTTPException(status_code=400, detail="invalid_effect")
    
    # TODO Phase 4: Implement full policy storage and evaluation engine
    # For now, return acknowledgment response (stub)
    pol = PolicyResponse(
        id=req.policy_id,  # Use policy_id as id for React-Admin
        policy_id=req.policy_id,
        version=req.version,
        resource_type=req.resource_type,
        condition_expression=req.condition_expression,
        effect=req.effect,
        created_by="system",
        created_at="now",
    )
    return pol


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    response: Response,
    session: AsyncSession = Depends(get_db_session)
) -> list[PolicyResponse]:
    """List policies (Phase 3: database-backed stub)."""
    # TODO Phase 4: Implement actual policy storage and retrieval
    # For now, return empty list as policies are not yet stored in database
    policy_responses = []
    
    # Add Content-Range header for React-Admin pagination
    total = len(policy_responses)
    response.headers["Content-Range"] = f"policies 0-{total-1 if total > 0 else 0}/{total}"
    
    return policy_responses

__all__ = ["router"]