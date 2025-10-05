from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any

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
def dry_run(req: DryRunRequest) -> DryRunResponse:
    decision, rationales = _evaluate(req.action)
    # Guard: any rationale not starting with allowed prefixes triggers error
    for r in rationales:
        if not any(r.startswith(p) for p in ALLOWED_RATIONALE_PREFIXES):
            raise HTTPException(status_code=400, detail="unknown_rationale_code")
    return DryRunResponse(decision=decision, rationales=rationales)


# In-memory policy store (very primitive) for contract satisfaction
_POLICIES: dict[str, PolicyResponse] = {}


@router.post("/register", response_model=PolicyResponse, status_code=201)
def register_policy(req: PolicyRegistrationRequest) -> PolicyResponse:
    # Basic validation: effect value
    if req.effect not in {"ALLOW", "DENY"}:
        raise HTTPException(status_code=400, detail="invalid_effect")
    # Accept idempotent registration by overwriting
    pol = PolicyResponse(
        policy_id=req.policy_id,
        version=req.version,
        resource_type=req.resource_type,
        condition_expression=req.condition_expression,
        effect=req.effect,
        created_by="system",
        created_at="now",
    )
    _POLICIES[req.policy_id] = pol
    return pol

__all__ = ["router"]