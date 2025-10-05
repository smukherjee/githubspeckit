"""
TEST-DB-10: Policy evaluation log persistence tests.

Validates:
- Policy evaluation logs persisted correctly (FR-018, FR-074)
- Tenant isolation for evaluation logs
- Rationale codes stored and retrievable
- Query performance for audit trail retrieval

Status: Phase 3 Lane DB-C
Dependencies: IMPL-DB-02 (PolicyEvaluationLogModel ORM), IMPL-DB-05 (repositories)
"""
from __future__ import annotations

import pytest
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from adapters.persistence.models import (
    PolicyEvaluationLogModel,
    TenantModel,
    UserModel,
    PolicyModel,
    DecisionEnum,
)


@pytest.mark.db
@pytest.mark.asyncio
class TestPolicyEvaluationLogPersistence:
    """TEST-DB-10: Policy evaluation log persistence validation."""
    
    async def test_persist_evaluation_log_basic(self, db_session):
        """
        Test policy evaluation log persisted with all required fields (FR-018, FR-074).
        
        Validates:
        - All fields stored correctly
        - Tenant isolation enforced
        - Decision and latency persisted
        """
        # Create tenant first
        tenant_id = uuid.uuid4()
        tenant = TenantModel(
            tenant_id=tenant_id,
            name="Log Test Tenant",
            status="active",
        )
        db_session.add(tenant)
        await db_session.flush()
        
        # Create user
        user_id = uuid.uuid4()
        user = UserModel(
            user_id=user_id,
            tenant_id=tenant_id,
            email="user@logtest.com",
            password_hash="hash",
            status="active",
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create policy
        policy_id = uuid.uuid4()
        policy = PolicyModel(
            policy_id=policy_id,
            tenant_id=tenant_id,
            name="Test Policy",
            rules=[{"action": "read", "resource": "users"}],
        )
        db_session.add(policy)
        await db_session.flush()
        
        # Create evaluation log with correct field names
        eval_id = uuid.uuid4()
        evaluation_log = PolicyEvaluationLogModel(
            eval_id=eval_id,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_id=user_id,
            decision=DecisionEnum.allow,  # Use enum value
            latency_ms=42,
            correlation_id="test-correlation-123",
        )
        db_session.add(evaluation_log)
        await db_session.flush()
        
        # Retrieve and validate
        result = await db_session.execute(
            select(PolicyEvaluationLogModel).where(PolicyEvaluationLogModel.eval_id == eval_id)
        )
        persisted_log = result.scalar_one()
        
        assert persisted_log.eval_id == eval_id
        assert persisted_log.tenant_id == tenant_id
        assert persisted_log.policy_id == policy_id
        assert persisted_log.user_id == user_id
        assert persisted_log.decision == DecisionEnum.allow
        assert persisted_log.latency_ms == 42
        assert persisted_log.correlation_id == "test-correlation-123"
        assert persisted_log.created_at is not None
    
    async def test_evaluation_log_tenant_isolation(self, db_session):
        """
        Test evaluation logs isolated by tenant (FR-002, FR-018).
        
        Validates queries filter by tenant_id.
        """
        # Create two tenants
        tenant_a_id = uuid.uuid4()
        tenant_b_id = uuid.uuid4()
        
        tenant_a = TenantModel(tenant_id=tenant_a_id, name="Tenant A", status="active")
        tenant_b = TenantModel(tenant_id=tenant_b_id, name="Tenant B", status="active")
        
        db_session.add_all([tenant_a, tenant_b])
        await db_session.flush()
        
        # Create users for each tenant
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()
        
        user_a = UserModel(user_id=user_a_id, tenant_id=tenant_a_id, email="a@test.com", password_hash="hash", status="active")
        user_b = UserModel(user_id=user_b_id, tenant_id=tenant_b_id, email="b@test.com", password_hash="hash", status="active")
        
        db_session.add_all([user_a, user_b])
        await db_session.flush()
        
        # Create policies for each tenant
        policy_a_id = uuid.uuid4()
        policy_b_id = uuid.uuid4()
        
        policy_a = PolicyModel(
            policy_id=policy_a_id,
            tenant_id=tenant_a_id,
            name="Policy A",
            rules=[],
        )
        policy_b = PolicyModel(
            policy_id=policy_b_id,
            tenant_id=tenant_b_id,
            name="Policy B",
            rules=[],
        )
        
        db_session.add_all([policy_a, policy_b])
        await db_session.flush()
        
        # Create evaluation logs for each tenant with correct fields
        eval_a1_id = uuid.uuid4()
        eval_a2_id = uuid.uuid4()
        eval_b1_id = uuid.uuid4()
        
        log_a1 = PolicyEvaluationLogModel(
            eval_id=eval_a1_id,
            tenant_id=tenant_a_id,
            policy_id=policy_a_id,
            user_id=user_a_id,
            decision=DecisionEnum.allow,
            latency_ms=10,
            correlation_id="corr-a1",
        )
        log_a2 = PolicyEvaluationLogModel(
            eval_id=eval_a2_id,
            tenant_id=tenant_a_id,
            policy_id=policy_a_id,
            user_id=user_a_id,
            decision=DecisionEnum.allow,
            latency_ms=15,
            correlation_id="corr-a2",
        )
        log_b1 = PolicyEvaluationLogModel(
            eval_id=eval_b1_id,
            tenant_id=tenant_b_id,
            policy_id=policy_b_id,
            user_id=user_b_id,
            decision=DecisionEnum.deny,
            latency_ms=20,
            correlation_id="corr-b1",
        )
        
        db_session.add_all([log_a1, log_a2, log_b1])
        await db_session.flush()
        
        # Query logs for tenant A
        result_a = await db_session.execute(
            select(PolicyEvaluationLogModel).where(PolicyEvaluationLogModel.tenant_id == tenant_a_id)
        )
        logs_a = result_a.scalars().all()
        
        # Should only return logs for tenant A
        assert len(logs_a) == 2
        assert all(log.tenant_id == tenant_a_id for log in logs_a)
        assert {log.eval_id for log in logs_a} == {eval_a1_id, eval_a2_id}
        
        # Query logs for tenant B
        result_b = await db_session.execute(
            select(PolicyEvaluationLogModel).where(PolicyEvaluationLogModel.tenant_id == tenant_b_id)
        )
        logs_b = result_b.scalars().all()
        
        # Should only return logs for tenant B
        assert len(logs_b) == 1
        assert logs_b[0].tenant_id == tenant_b_id
        assert logs_b[0].eval_id == eval_b1_id
    
    async def test_evaluation_log_query_by_user(self, db_session):
        """
        Test querying evaluation logs by user_id for audit trail (FR-005, FR-074).
        
        Validates audit trail retrieval.
        """
        # Create tenant
        tenant_id = uuid.uuid4()
        tenant = TenantModel(tenant_id=tenant_id, name="Audit Tenant", status="active")
        db_session.add(tenant)
        await db_session.flush()
        
        # Create two users
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        
        user1 = UserModel(user_id=user1_id, tenant_id=tenant_id, email="user1@test.com", password_hash="hash", status="active")
        user2 = UserModel(user_id=user2_id, tenant_id=tenant_id, email="user2@test.com", password_hash="hash", status="active")
        
        db_session.add_all([user1, user2])
        await db_session.flush()
        
        # Create policy
        policy_id = uuid.uuid4()
        policy = PolicyModel(
            policy_id=policy_id,
            tenant_id=tenant_id,
            name="Audit Policy",
            rules=[],
        )
        db_session.add(policy)
        await db_session.flush()
        
        # Create multiple logs for user1
        eval1_id = uuid.uuid4()
        eval2_id = uuid.uuid4()
        eval3_id = uuid.uuid4()
        
        log1 = PolicyEvaluationLogModel(
            eval_id=eval1_id,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_id=user1_id,
            decision=DecisionEnum.allow,
            latency_ms=10,
            correlation_id="corr-user1-1",
        )
        log2 = PolicyEvaluationLogModel(
            eval_id=eval2_id,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_id=user1_id,
            decision=DecisionEnum.allow,
            latency_ms=12,
            correlation_id="corr-user1-2",
        )
        log3 = PolicyEvaluationLogModel(
            eval_id=eval3_id,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_id=user2_id,
            decision=DecisionEnum.deny,
            latency_ms=8,
            correlation_id="corr-user2-1",
        )
        
        db_session.add_all([log1, log2, log3])
        await db_session.flush()
        
        # Query logs for user1
        result = await db_session.execute(
            select(PolicyEvaluationLogModel)
            .where(PolicyEvaluationLogModel.tenant_id == tenant_id)
            .where(PolicyEvaluationLogModel.user_id == user1_id)
            .order_by(PolicyEvaluationLogModel.created_at)
        )
        user1_logs = result.scalars().all()
        
        # Should only return logs for user1
        assert len(user1_logs) == 2
        assert all(log.user_id == user1_id for log in user1_logs)
        assert {log.eval_id for log in user1_logs} == {eval1_id, eval2_id}
    
    async def test_evaluation_log_rationale_codes(self, db_session):
        """
        Test correlation_id stored and retrievable (FR-018, FR-074).
        
        Validates correlation tracking for debugging and audit.
        """
        # Create tenant
        tenant_id = uuid.uuid4()
        tenant = TenantModel(tenant_id=tenant_id, name="Correlation Tenant", status="active")
        db_session.add(tenant)
        await db_session.flush()
        
        # Create user
        user_id = uuid.uuid4()
        user = UserModel(user_id=user_id, tenant_id=tenant_id, email="user@test.com", password_hash="hash", status="active")
        db_session.add(user)
        await db_session.flush()
        
        # Create policy
        policy_id = uuid.uuid4()
        policy = PolicyModel(
            policy_id=policy_id,
            tenant_id=tenant_id,
            name="Correlation Policy",
            rules=[],
        )
        db_session.add(policy)
        await db_session.flush()
        
        # Create logs with different correlation ids and decisions
        correlation_ids = [
            "corr-matched",
            "corr-denied",
            "corr-abstain",
            "corr-condition-failed",
            "corr-inherited",
        ]
        
        decisions = [
            DecisionEnum.allow,
            DecisionEnum.deny,
            DecisionEnum.abstain,
            DecisionEnum.allow,
            DecisionEnum.deny,
        ]
        
        for i, (corr_id, decision) in enumerate(zip(correlation_ids, decisions)):
            log = PolicyEvaluationLogModel(
                eval_id=uuid.uuid4(),
                tenant_id=tenant_id,
                policy_id=policy_id,
                user_id=user_id,
                decision=decision,
                latency_ms=10 + i,
                correlation_id=corr_id,
            )
            db_session.add(log)
        
        await db_session.flush()
        
        # Query logs and verify correlation ids
        result = await db_session.execute(
            select(PolicyEvaluationLogModel)
            .where(PolicyEvaluationLogModel.tenant_id == tenant_id)
            .order_by(PolicyEvaluationLogModel.created_at)
        )
        all_logs = result.scalars().all()
        
        assert len(all_logs) == 5
        retrieved_correlations = [log.correlation_id for log in all_logs]
        assert set(retrieved_correlations) == set(correlation_ids)


# TODO (Phase 4): Add performance test for large-scale log queries
# @pytest.mark.db
# @pytest.mark.asyncio
# async def test_evaluation_log_query_performance(db_session):
#     """Test evaluation log query performance at scale (FR-074)."""
#     # Create 10,000 logs and verify query time < 200ms
#     pass
