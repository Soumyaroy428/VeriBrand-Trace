"""End-to-End System Integration, Health Telemetry, and Production Release Readiness Tests."""

import hashlib
import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.documents import (
    User,
    Workspace,
    Membership,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    Approval,
    ComplianceCertificate,
    AuditEvent,
)
from app.core.security import create_access_token
from app.services.audit_verifier import verify_workspace_audit_chain


@pytest.fixture
async def setup_ops_test_env():
    """Sets up a brand workspace with admin and creator users."""
    ws = Workspace(name="Acme Enterprise Holdings", slug="acme-enterprise")
    await ws.insert()

    admin = User(
        email="ops_admin@veribrand.io",
        hashed_password="TestAdminPassword123",
        full_name="Operations Administrator",
        is_active=True,
    )
    await admin.insert()

    creator = User(
        email="ops_creator@veribrand.io",
        hashed_password="TestCreatorPassword123",
        full_name="Operations Content Creator",
        is_active=True,
    )
    await creator.insert()

    admin_mem = Membership(workspace_id=ws.id, user_id=admin.id, role="GOVERNANCE_ADMIN")
    await admin_mem.insert()

    creator_mem = Membership(workspace_id=ws.id, user_id=creator.id, role="CREATOR")
    await creator_mem.insert()

    admin_token = create_access_token(subject=admin.id, email=admin.email)
    creator_token = create_access_token(subject=creator.id, email=creator.email)

    return {
        "workspace": ws,
        "admin": admin,
        "creator": creator,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "creator_headers": {"Authorization": f"Bearer {creator_token}"},
    }


@pytest.mark.asyncio
async def test_system_telemetry_endpoint(setup_ops_test_env):
    """Verifies that the telemetry endpoint reports all active engines and release gates."""
    env = setup_ops_test_env
    ws_id = env["workspace"].id
    headers = env["admin_headers"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/workspaces/{ws_id}/system/telemetry",
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["workspace_id"] == ws_id
    assert data["overall_status"] == "OPERATIONAL"
    assert "deterministic_engine" in data["engines"]
    assert "rag_service" in data["engines"]
    assert "audit_ledger" in data["engines"]
    assert "batch_processor" in data["engines"]
    assert "privacy_gate" in data["engines"]
    assert data["release_gates"]["philosophy_suggest_never_override_enforced"] is True
    assert data["release_gates"]["cryptographic_ledger_tamper_evident"] is True
    assert "Sayantan Dutta" in data["team_signoff"].values()
    assert "Soumya Roy" in data["team_signoff"].values()
    assert "Debarun Banerjee" in data["team_signoff"].values()
    assert "Risijit Dhar" in data["team_signoff"].values()


@pytest.mark.asyncio
async def test_workspace_backup_and_cryptographic_seal(setup_ops_test_env):
    """Verifies generating a sealed disaster recovery backup archive."""
    env = setup_ops_test_env
    ws_id = env["workspace"].id
    headers = env["admin_headers"]

    # Seed an approved fact and rule
    fact = ApprovedFact(
        workspace_id=ws_id,
        fact_key="enterprise_transactions",
        statement="Acme Global powers 500 million enterprise transactions daily.",
        created_by=env["admin"].id,
    )
    await fact.insert()

    term = TerminologyRule(
        workspace_id=ws_id,
        term="cheap",
        rule_type="BANNED",
        replacement="cost-effective",
        created_by=env["admin"].id,
    )
    await term.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/system/backup",
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["workspace_id"] == ws_id
    assert "backup_seal_sha256" in data
    assert len(data["backup_seal_sha256"]) == 64
    assert data["entities_backed_up"]["approved_facts"] >= 1
    assert data["entities_backed_up"]["terminology_rules"] >= 1

    # Verify backup event in audit ledger
    events = await AuditEvent.find(
        AuditEvent.workspace_id == ws_id,
        AuditEvent.action == "WORKSPACE_BACKUP_CREATED",
    ).to_list()
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_non_admin_cannot_trigger_backup(setup_ops_test_env):
    """Verifies that non-admin members are rejected when attempting backup operations."""
    env = setup_ops_test_env
    ws_id = env["workspace"].id
    creator_headers = env["creator_headers"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/system/backup",
            headers=creator_headers,
        )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_full_governance_lifecycle_end_to_end(setup_ops_test_env):
    """Verifies complete end-to-end audit lifecycle from draft to approval and certificate."""
    env = setup_ops_test_env
    ws_id = env["workspace"].id
    admin_headers = env["admin_headers"]

    # 1. Create a submission
    submission = Submission(
        workspace_id=ws_id,
        title="Enterprise Product Whitepaper",
        input_type="TEXT",
        created_by=env["creator"].id,
        status="DRAFT",
    )
    await submission.insert()

    raw_text = "Acme Global delivers unmatched enterprise cloud performance."
    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    rev = SubmissionRevision(
        submission_id=submission.id,
        revision_number=1,
        content_hash=content_hash,
        raw_content=raw_text,
        extracted_text=raw_text,
        sanitized_text=raw_text,
        created_by=env["creator"].id,
    )
    await rev.insert()

    # 2. Trigger Audit
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        audit_res = await ac.post(
            f"/api/v1/submissions/{submission.id}/audits",
            headers=admin_headers,
        )
    assert audit_res.status_code == 201

    # 3. Reviewer signs off and approves
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        approval_res = await ac.post(
            f"/api/v1/submissions/{submission.id}/approve",
            json={"comments": "Verified compliant with brand messaging standards."},
            headers=admin_headers,
        )
    assert approval_res.status_code == 200
    approval_data = approval_res.json()
    assert approval_data["decision"] == "APPROVED"
    assert approval_data["certificate"]["certificate_number"] is not None

    # 4. Verify Cryptographic Ledger Chain Integrity
    verification = await verify_workspace_audit_chain(ws_id)
    assert verification.is_valid is True
    assert verification.verified_events >= 2
