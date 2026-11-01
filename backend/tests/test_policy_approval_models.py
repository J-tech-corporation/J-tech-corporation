"""Tests for policy approval ORM models."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.models import Base, Policy, PolicyApprovalRequest, PolicyApprovalReview


def test_policy_approval_tables_and_constraints_exist() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert "policy_approval_requests" in inspector.get_table_names()
    assert "policy_approval_reviews" in inspector.get_table_names()

    constraints = {
        item["name"] for item in inspector.get_unique_constraints("policy_approval_reviews")
    }
    assert "uq_policy_approval_reviews_request_reviewer_type" in constraints


def test_policy_approval_request_and_review_relationships() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        policy = Policy(
            policy_key="test.policy",
            name="Test Policy",
            description=None,
            policy_type="BUSINESS",
            scope_type="GLOBAL",
            scope_id=None,
            status="DRAFT",
            current_version="1.0.0",
            rules=None,
            created_by="test-agent",
        )
        request = PolicyApprovalRequest(
            policy=policy,
            policy_version="1.0.0",
            snapshot_hash="a" * 64,
            requested_by="test-agent",
            status="PENDING_APPROVAL",
            reason="Initial review",
            submitted_at=datetime.now(UTC),
        )
        review = PolicyApprovalReview(
            approval_request=request,
            reviewer_id="ceo",
            review_type="POLICY",
            decision="APPROVE",
            comments="Reviewed",
            reviewed_at=datetime.now(UTC),
        )
        session.add(request)
        session.flush()

        assert request.policy_id == policy.id
        assert review.approval_request_id == request.id
        assert request.reviews == [review]
