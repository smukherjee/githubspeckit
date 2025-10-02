"""Basic policy evaluator (IMPL-POL-02).

Implements a tiny policy evaluation model for Phase 2 to satisfy TEST-POL-01.
- Policies have: policy_id, version, resource_type, condition (callable/predicate), effect (ALLOW/DENY)
- Evaluator returns ALLOW/DENY/ABSTAIN with rationale code when DENY.

This is intentionally minimal: condition is represented as a Python callable that
accepts context dict and returns truthy/falsey. In production this would be a
parsed expression or compiled predicate loaded from policy registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Any, List, Optional


class Decision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


@dataclass
class Policy:
    policy_id: str
    version: int
    resource_type: str
    condition: Callable[[Dict[str, Any]], bool]
    effect: Decision
    created_by: Optional[str] = None


@dataclass
class EvalResult:
    decision: Decision
    reason: Optional[str] = None


class PolicyEvaluator:
    def __init__(self, policies: Optional[List[Policy]] = None, *, valid_roles: Optional[List[str]] = None) -> None:
        # policies keyed by resource_type -> list(policy) sorted by version desc
        self._policies: Dict[str, List[Policy]] = {}
        self.valid_roles = set(valid_roles or [])
        # active version per resource_type (for rollback) - None means latest
        self._active_version: Dict[str, Optional[int]] = {}
        for p in policies or []:
            self.register(p)

    def register(self, policy: Policy) -> None:
        lst = self._policies.setdefault(policy.resource_type, [])
        for ex in lst:
            if ex.version == policy.version:
                raise ValueError("policy version conflict")
        lst.append(policy)
        lst.sort(key=lambda x: x.version, reverse=True)

    def set_active_version(self, resource_type: str, version: Optional[int]) -> None:
        """Activate a specific version or None for newest (rollback mechanism)."""
        self._active_version[resource_type] = version

    def _iter_effective_policies(self, resource_type: str) -> List[Policy]:
        lst = self._policies.get(resource_type, [])
        active_version = self._active_version.get(resource_type)
        if active_version is None:
            return lst
        # filter only that version if present
        return [p for p in lst if p.version == active_version]

    def evaluate(self, resource_type: str, context: Dict[str, Any]) -> EvalResult:
        # Role enforcement guard (undefined roles) - if roles provided in context
        roles = context.get("roles") or []
        if self.valid_roles and any(r not in self.valid_roles for r in roles):
            return EvalResult(decision=Decision.DENY, reason="undefined_role")

        # Implicit tenant_admin allowance (FR-066): if tenant_admin present and action not restricted
        # We rely on context flag 'restricted_action' set by higher layer for operations requiring explicit policy.
        # If not restricted, short-circuit ALLOW.
        if "tenant_admin" in roles and not context.get("restricted_action"):
            return EvalResult(decision=Decision.ALLOW, reason="implicit_tenant_admin_allow")

        lst = self._iter_effective_policies(resource_type)
        if not lst:
            return EvalResult(decision=Decision.ABSTAIN)
        for p in lst:
            try:
                if p.condition(context):
                    return EvalResult(decision=p.effect, reason=f"policy:{p.policy_id}:v{p.version}")
            except Exception:
                continue
        return EvalResult(decision=Decision.ABSTAIN)


__all__ = ["PolicyEvaluator", "Policy", "Decision", "EvalResult"]
