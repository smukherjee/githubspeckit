"""Admin scope validator (IMPL-POL-10) enforcing defense-in-depth layers (C-026, FR-036).

Layers (validated in this order):
 1. Authentication principal present (context['principal'])
 2. Administrative role present (superadmin OR tenant_admin)
 3. Policy evaluation (DENY overrides success)
 4. Explicit admin scope indicator (context['admin_scope_explicit'] == True)

Missing required layers (1,2,4) -> AdminScopeError code 'admin_scope_missing_layer'.
Policy DENY -> AdminScopeError code 'admin_scope_policy_denied'.
Success returns AdminScopeSuccess with decision (ALLOW/ABSTAIN) and layers.

Audit emission is performed by higher layers after success (out-of-scope here).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from .evaluator import PolicyEvaluator, Decision, EvalResult


class AdminScopeError(Exception):
    def __init__(self, code: str, *, layers: List[str] | None = None, policy_reason: str | None = None):
        self.code = code
        self.layers = layers or []
        self.policy_reason = policy_reason
        msg = code
        if self.layers:
            msg += f" missing={self.layers}"
        if policy_reason:
            msg += f" policy_reason={policy_reason}"
        super().__init__(msg)


@dataclass
class AdminScopeSuccess:
    decision: Decision
    policy_reason: str | None
    satisfied_layers: List[str]


class AdminScopeValidator:
    def __init__(self, evaluator: PolicyEvaluator):
        self._evaluator = evaluator

    def validate(self, resource_type: str, context: Dict[str, Any]) -> AdminScopeSuccess:
        missing: List[str] = []

        principal = context.get("principal")
        if not principal:
            missing.append("principal")

        roles: List[str] = context.get("roles") or []
        if not any(r in ("superadmin", "tenant_admin") for r in roles):
            missing.append("admin_role")

        if not context.get("admin_scope_explicit"):
            missing.append("explicit_scope")

        if missing:
            raise AdminScopeError("admin_scope_missing_layer", layers=missing)

        eval_result: EvalResult = self._evaluator.evaluate(resource_type, context)
        if eval_result.decision == Decision.DENY:
            raise AdminScopeError("admin_scope_policy_denied", policy_reason=eval_result.reason)

        return AdminScopeSuccess(
            decision=eval_result.decision,
            policy_reason=eval_result.reason,
            satisfied_layers=["principal", "admin_role", "explicit_scope", "policy_eval"],
        )


__all__ = [
    "AdminScopeValidator",
    "AdminScopeError",
    "AdminScopeSuccess",
]
