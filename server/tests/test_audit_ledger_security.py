"""Automated tests for Checkpoint 11: Security Hardening, Audit Trail Verification,
and Tamper-Evident Ledger Integrity.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.documents import User, Workspace, Membership, AuditEvent, Submission, SubmissionRevision
from app.core.security import get_password_hash, create_access_token
from app.services.audit_verifier import (
    record_audit_event,
    verify_workspace_audit_chain,
)


@pytest.mark.asyncio
async def test_unbroken_audit_chain_verification():
    """Verify that sequentially chained audit events produce a 100% verified ledger."""
    ws = Workspace(name="Integrity Brand", slug="integrity-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="admin_integrity@brand.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Integrity Admin",
    )
    await admin.insert()

    # Append 4 sequential events
    ev1 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Workspace",
        entity_id=ws.id,
        action="WORKSPACE_INITIALIZED",
        metadata_json={"slug": ws.slug},
    )
    assert ev1.previous_hash is None

    ev2 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Submission",
        entity_id="sub-101",
        action="SUBMISSION_CREATED",
        metadata_json={"title": "Q1 Report"},
    )
    assert ev2.previous_hash == ev1.event_hash

    ev3 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Submission",
        entity_id="sub-101",
        action="PRIVACY_GATE_PASSED",
        metadata_json={"scrubbed": True},
    )
    assert ev3.previous_hash == ev2.event_hash

    ev4 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Submission",
        entity_id="sub-101",
        action="SUBMISSION_APPROVED",
        metadata_json={"score": 95},
    )
    assert ev4.previous_hash == ev3.event_hash

    # Run cryptographic verification
    report = await verify_workspace_audit_chain(ws.id)
    assert report.is_valid is True
    assert report.status == "VERIFIED_INTACT"
    assert report.total_events == 4
    assert report.verified_events == 4
    assert report.corrupted_count == 0
    assert report.genesis_hash == ev1.event_hash
    assert report.latest_hash == ev4.event_hash


@pytest.mark.asyncio
async def test_tampering_detection_modified_payload():
    """Verify that modifying an event payload directly in the database is caught as tampering."""
    ws = Workspace(name="Tamper Test Brand", slug="tamper-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="admin_tamper@brand.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Admin",
    )
    await admin.insert()

    ev1 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Submission",
        entity_id="sub-201",
        action="SUBMISSION_CREATED",
        metadata_json={"title": "Original Title"},
    )
    ev2 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Submission",
        entity_id="sub-201",
        action="SUBMISSION_REJECTED",
        metadata_json={"reason": "Contains banned terms"},
    )

    # Maliciously tamper with event 2 in the database without updating the SHA-256 hash
    ev2.action = "SUBMISSION_APPROVED"
    ev2.metadata_json["reason"] = "Forged approval"
    await ev2.save()

    report = await verify_workspace_audit_chain(ws.id)
    assert report.is_valid is False
    assert report.status == "TAMPERING_DETECTED"
    assert report.corrupted_count >= 1
    assert any(c.event_id == ev2.id for c in report.corrupted_events)
    assert any("Payload altered" in c.reason for c in report.corrupted_events)


@pytest.mark.asyncio
async def test_tampering_detection_broken_chain_link():
    """Verify that altering previous_hash is caught as a broken chain link."""
    ws = Workspace(name="Fork Test Brand", slug="fork-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="admin_fork@brand.com",
        hashed_password=get_password_hash("Pass123!"),
    )
    await admin.insert()

    ev1 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Asset",
        entity_id="asset-1",
        action="ASSET_UPLOADED",
    )
    ev2 = await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="Asset",
        entity_id="asset-2",
        action="ASSET_UPLOADED",
    )

    # Break link
    ev2.previous_hash = "0" * 64
    await ev2.save()

    report = await verify_workspace_audit_chain(ws.id)
    assert report.is_valid is False
    assert report.status == "TAMPERING_DETECTED"
    assert any("Broken chain link" in c.reason for c in report.corrupted_events)


@pytest.mark.asyncio
async def test_audit_trail_api_filters_and_pagination():
    """Verify GET /api/v1/workspaces/{workspace_id}/audit-trail endpoint."""
    ws = Workspace(name="API Brand", slug="api-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="admin_api_trail@brand.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Security Admin",
    )
    await admin.insert()

    await Membership(workspace_id=ws.id, user_id=admin.id, role="GOVERNANCE_ADMIN").insert()

    token = create_access_token(subject=admin.id, email=admin.email)

    # Seed events
    for i in range(5):
        await record_audit_event(
            workspace_id=ws.id,
            actor_user_id=admin.id,
            entity_type="Submission",
            entity_id=f"sub-{i}",
            action="SUBMISSION_CREATED" if i % 2 == 0 else "SUBMISSION_APPROVED",
            metadata_json={"index": i},
        )

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # All events paginated limit=2
        res = await ac.get(f"/api/v1/workspaces/{ws.id}/audit-trail?limit=2&skip=0", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["has_more"] is True

        # Filter by action
        res_filter = await ac.get(
            f"/api/v1/workspaces/{ws.id}/audit-trail?action=SUBMISSION_APPROVED",
            headers=headers,
        )
        assert res_filter.status_code == 200
        data_filter = res_filter.json()
        assert data_filter["total"] == 2
        assert all(it["action"] == "SUBMISSION_APPROVED" for it in data_filter["items"])


@pytest.mark.asyncio
async def test_audit_trail_verify_endpoint():
    """Verify GET /api/v1/workspaces/{workspace_id}/audit-trail/verify."""
    ws = Workspace(name="Verify API Brand", slug="verify-api-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="reviewer_trail@brand.com",
        hashed_password=get_password_hash("Pass123!"),
    )
    await admin.insert()

    await Membership(workspace_id=ws.id, user_id=admin.id, role="REVIEWER").insert()

    token = create_access_token(subject=admin.id, email=admin.email)

    await record_audit_event(
        workspace_id=ws.id,
        actor_user_id=admin.id,
        entity_type="BrandVault",
        entity_id="rule-1",
        action="RULE_CREATED",
    )

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/workspaces/{ws.id}/audit-trail/verify", headers=headers)

    assert res.status_code == 200
    report = res.json()
    assert report["is_valid"] is True
    assert report["status"] == "VERIFIED_INTACT"
    assert report["total_events"] == 1


@pytest.mark.asyncio
async def test_security_posture_endpoint():
    """Verify GET /api/v1/workspaces/{workspace_id}/security/posture."""
    ws = Workspace(name="Posture Brand", slug="posture-brand", status="ACTIVE")
    await ws.insert()

    admin = User(
        email="admin_posture@brand.com",
        hashed_password=get_password_hash("Pass123!"),
    )
    await admin.insert()

    await Membership(workspace_id=ws.id, user_id=admin.id, role="GOVERNANCE_ADMIN").insert()

    # Submission and revision with privacy metadata
    sub = Submission(
        workspace_id=ws.id,
        created_by=admin.id,
        title="Privacy Clean Submission",
        input_type="TEXT",
        status="APPROVED",
    )
    await sub.insert()

    rev = SubmissionRevision(
        submission_id=sub.id,
        revision_number=1,
        content_hash="hash123",
        created_by=admin.id,
        privacy_gate_metadata={
            "scrubbed": True,
            "pii_entities": ["EMAIL", "PHONE"],
            "confidential_terms_masked": ["PROJECT_PEGASUS"],
        },
    )
    await rev.insert()

    token = create_access_token(subject=admin.id, email=admin.email)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/workspaces/{ws.id}/security/posture", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["workspace_name"] == "Posture Brand"
    assert data["privacy_gate_stats"]["total_submissions_scrubbed"] == 1
    assert data["privacy_gate_stats"]["total_pii_entities_redacted"] == 2
    assert data["privacy_gate_stats"]["total_confidential_terms_masked"] == 1
    assert data["rbac_posture"]["governance_admins_count"] == 1
    assert data["rbac_posture"]["tenant_isolation_enforced"] is True


@pytest.mark.asyncio
async def test_unauthorized_cross_workspace_audit_denied():
    """Verify cross-workspace audit access is rejected with HTTP 403."""
    ws1 = Workspace(name="Brand 1", slug="brand-1", status="ACTIVE")
    await ws1.insert()

    ws2 = Workspace(name="Brand 2", slug="brand-2", status="ACTIVE")
    await ws2.insert()

    user2 = User(
        email="user_ws2@brand.com",
        hashed_password=get_password_hash("Pass123!"),
    )
    await user2.insert()
    await Membership(workspace_id=ws2.id, user_id=user2.id, role="CREATOR").insert()

    token = create_access_token(subject=user2.id, email=user2.email)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # User in ws2 attempts to read ws1 audit trail
        res = await ac.get(f"/api/v1/workspaces/{ws1.id}/audit-trail", headers=headers)

    assert res.status_code == 403
    assert "does not have access to this workspace" in res.json()["detail"]
