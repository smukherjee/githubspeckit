from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

class Decision(str, Enum):
    allow = "ALLOW"
    deny = "DENY"
    abstain = "ABSTAIN"

class PolicyStatus(str, Enum):
    """Policy lifecycle status (soft-delete pattern)."""
    active = "active"
    disabled = "disabled"  # Soft-deleted state

@dataclass
class PolicyRule:
    rule_id: str
    version: int
    resource: str
    action: str
    effect: Decision
    condition: Optional[Dict[str, Any]] = None  # Structure validated by extension predicates

@dataclass
class Policy:
    policy_id: str
    tenant_id: str
    name: str
    rules: List[PolicyRule] = field(default_factory=list)
    status: PolicyStatus = PolicyStatus.active  # Soft-delete support
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

class PolicyRepository:
    def __init__(self) -> None:
        self._store: dict[str, Policy] = {}

    def upsert(self, policy: Policy) -> Policy:
        self._store[policy.policy_id] = policy
        return policy

    def get(self, policy_id: str) -> Optional[Policy]:
        return self._store.get(policy_id)

    def list_by_tenant(self, tenant_id: str) -> list[Policy]:
        return [p for p in self._store.values() if p.tenant_id == tenant_id]
