"""Automated tests for Reviewer Sign-Off, Comments, Exceptions, Compliance Certificates, and Governance Analytics."""

import hashlib
import json
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.core.database import init_db
from app.core.security import get_password_hash, create_access_token
from app.models.documents import (
    User,
    Workspace,
    Membership,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    ExceptionRequest,
    ReviewComment,
    Approval,
    ComplianceCertificate,
    AuditEvent,
)


@pytest.fixture
def auth_headers_factory():
    """Generates bearer auth headers for a given user."""
    def _create_headers(user: User):
        token = create_access_token(subject=user.id, email=user.email)
        return {"Authorization": f"Bearer {token}"}
    return _create_headers


async def create_workspace_and_users():
    """Helper to scaffold workspace with Creator, Reviewer, and Governance Admin."""
    ws = Workspace(
        id="ws-test-rev",
        name="Acme Corp",
        slug="acme-corp",
        created_at=datetime.now(timezone.utc),
    )
    await ws.insert()

    creator = User(
        id="user-creator",
        email="creator@acme.com",
        hashed_password=get_password_hash("CreatorPass123!"),
        full_name="Alice Creator",
        is_active=True,
    )
    await creator.insert()

    reviewer = User(
        id="user-reviewer",
        email="reviewer@acme.com",
        hashed_password=get_password_hash("ReviewerPass123!"),
        full_name="Bob Reviewer",
        is_active=True,
    )
    await reviewer.insert()

    admin = User(
        id="user-admin",
        email="admin@acme.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Carol Admin",
        is_active=True,
    )
    await admin.insert()

    await Membership(workspace_id=ws.id, user_id=creator.id, role="CREATOR").insert()
    await Membership(workspace_id=ws.id, user_id=reviewer.id, role="REVIEWER").insert()
    await Membership(workspace_id=ws.id, user_id=admin.id, role="GOVERNANCE_ADMIN").insert()

    return ws, creator, reviewer, admin


@pytest.mark.asyncio
async def test_reviewer_queue_retrieval(auth_headers_factory):
    """Test reviewer queue returns pending items with readiness score and finding counts."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    # Create submission and revision
    sub = Submission(
        id="sub-queue-1",
        workspace_id=ws.id,
        created_by=creator.id,
        title="Q4 Campaign",
        input_type="TEXT",
        status="PENDING_REVIEW",
    )
    await sub.insert()

    rev = SubmissionRevision(
        id="rev-queue-1",
        submission_id=sub.id,
        revision_number=1,
        raw_text_content="Superlative best in class campaign.",
        content_hash="hash-q4",
        created_by=creator.id,
    )
    await rev.insert()

    audit = AuditRun(
        id="audit-queue-1",
        submission_id=sub.id,
        revision_id=rev.id,
        readiness_score=85,
    )
    await audit.insert()

    finding = Finding(
        id="finding-queue-1",
        audit_run_id=audit.id,
        category="TERMINOLOGY",
        severity="HIGH",
        source_engine="DETERMINISTIC",
        title="Superlative tone",
        description="Avoid superlative claims",
    )
    await finding.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/workspaces/{ws.id}/reviews/queue",
            headers=auth_headers_factory(reviewer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_id"] == ws.id
        assert data["total_count"] == 1
        item = data["items"][0]
        assert item["submission_id"] == sub.id
        assert item["title"] == "Q4 Campaign"
        assert item["creator_email"] == creator.email
        assert item["readiness_score"] == 85
        assert item["high_findings"] == 1


@pytest.mark.asyncio
async def test_inline_review_comments_crud(auth_headers_factory):
    """Test adding and retrieving review comments with author metadata."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    sub = Submission(id="sub-comm-1", workspace_id=ws.id, created_by=creator.id, title="Pitch Deck", input_type="TEXT")
    await sub.insert()
    rev = SubmissionRevision(id="rev-comm-1", submission_id=sub.id, revision_number=1, content_hash="hash-comm", created_by=creator.id)
    await rev.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reviewer posts comment
        post_resp = await client.post(
            f"/api/v1/submissions/{sub.id}/comments",
            headers=auth_headers_factory(reviewer),
            json={
                "comment_text": "Please align the hero color with Pantone 286 C.",
                "anchor_location": {"line": 12, "highlight": "off-blue"},
            },
        )
        assert post_resp.status_code == 201
        post_data = post_resp.json()
        assert post_data["comment_text"] == "Please align the hero color with Pantone 286 C."
        assert post_data["user_email"] == reviewer.email

        # Creator views comments
        get_resp = await client.get(
            f"/api/v1/submissions/{sub.id}/comments",
            headers=auth_headers_factory(creator),
        )
        assert get_resp.status_code == 200
        comments = get_resp.json()
        assert len(comments) == 1
        assert comments[0]["user_name"] == "Bob Reviewer"
        assert comments[0]["anchor_location"]["line"] == 12


@pytest.mark.asyncio
async def test_exception_decision_recalculates_readiness_score(auth_headers_factory):
    """Test approving an exception updates finding to EXCEPTION_APPROVED and restores readiness score."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    sub = Submission(id="sub-exc-1", workspace_id=ws.id, created_by=creator.id, title="Special Event", input_type="TEXT")
    await sub.insert()
    rev = SubmissionRevision(id="rev-exc-1", submission_id=sub.id, revision_number=1, content_hash="hash-exc", created_by=creator.id)
    await rev.insert()

    audit = AuditRun(
        id="audit-exc-1",
        submission_id=sub.id,
        revision_id=rev.id,
        readiness_score=75,  # 100 - 25 = 75 due to critical finding
    )
    await audit.insert()

    finding = Finding(
        id="finding-exc-1",
        audit_run_id=audit.id,
        category="TERMINOLOGY",
        severity="CRITICAL",
        source_engine="DETERMINISTIC",
        title="Unapproved Slogan",
        description="Legacy slogan used",
        status="EXCEPTION_REQUESTED",
    )
    await finding.insert()

    exc = ExceptionRequest(
        id="exc-req-1",
        finding_id=finding.id,
        submission_id=sub.id,
        requested_by=creator.id,
        reason="Legacy branding explicitly required for retrospective campaign.",
        status="PENDING",
    )
    await exc.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/exceptions/{exc.id}/decide",
            headers=auth_headers_factory(reviewer),
            json={
                "decision": "APPROVED",
                "decision_note": "Approved for retrospective context.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["decided_by"] == reviewer.id

        # Verify finding status changed
        updated_f = await Finding.get(finding.id)
        assert updated_f.status == "EXCEPTION_APPROVED"

        # Verify audit run readiness score was recalculated back to 100!
        updated_audit = await AuditRun.get(audit.id)
        assert updated_audit.readiness_score == 100


@pytest.mark.asyncio
async def test_creator_cannot_approve_own_submission(auth_headers_factory):
    """Test strict governance rule: Creator cannot self-approve their own submission."""
    ws, creator, _, _ = await create_workspace_and_users()

    sub = Submission(
        id="sub-self-app",
        workspace_id=ws.id,
        created_by=creator.id,
        title="Self-Approval Attempt",
        input_type="TEXT",
        status="PENDING_REVIEW",
    )
    await sub.insert()

    rev = SubmissionRevision(id="rev-self-app", submission_id=sub.id, revision_number=1, content_hash="hash-self", created_by=creator.id)
    await rev.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/submissions/{sub.id}/approve",
            headers=auth_headers_factory(creator),
            json={"decision_notes": "I approve my own work."},
        )
        assert resp.status_code == 403
        assert "Creators cannot approve their own submissions" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reviewer_approval_issues_compliance_certificate(auth_headers_factory):
    """Test formal reviewer sign-off transitions status, issues certificate, and records chained audit events."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    sub = Submission(
        id="sub-app-1",
        workspace_id=ws.id,
        created_by=creator.id,
        title="Final Brand Book",
        input_type="TEXT",
        status="PENDING_REVIEW",
    )
    await sub.insert()

    rev = SubmissionRevision(
        id="rev-app-1",
        submission_id=sub.id,
        revision_number=1,
        content_hash="abc-content-hash-123",
        created_by=creator.id,
    )
    await rev.insert()

    audit = AuditRun(
        id="audit-app-1",
        submission_id=sub.id,
        revision_id=rev.id,
        readiness_score=95,
        summary_counts={"CRITICAL": 0, "HIGH": 0, "MEDIUM": 1, "LOW": 0},
    )
    await audit.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/submissions/{sub.id}/approve",
            headers=auth_headers_factory(reviewer),
            json={"decision_notes": "Excellent alignment with Acme brand guidelines."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "APPROVED"
        assert data["readiness_score_at_approval"] == 95
        assert data["certificate"] is not None
        cert = data["certificate"]
        assert cert["certificate_number"].startswith("VBT-CERT-")
        assert len(cert["certificate_hash"]) == 64  # SHA-256 hash length

        # Verify submission status changed
        updated_sub = await Submission.get(sub.id)
        assert updated_sub.status == "APPROVED"

        # Verify certificate saved in db
        saved_cert = await ComplianceCertificate.find_one(
            ComplianceCertificate.submission_id == sub.id
        )
        assert saved_cert is not None
        assert saved_cert.certificate_number == cert["certificate_number"]

        # Verify audit trail chained
        approved_event = await AuditEvent.find_one(AuditEvent.action == "SUBMISSION_APPROVED")
        assert approved_event is not None
        assert approved_event.actor_user_id == reviewer.id
        assert approved_event.previous_hash is None or isinstance(approved_event.previous_hash, str)

        cert_event = await AuditEvent.find_one(AuditEvent.action == "COMPLIANCE_CERTIFICATE_ISSUED")
        assert cert_event is not None
        assert cert_event.previous_hash == approved_event.event_hash


@pytest.mark.asyncio
async def test_reviewer_rejection_workflow(auth_headers_factory):
    """Test rejection transitions status to NEEDS_CHANGES and requires justification notes."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    sub = Submission(
        id="sub-rej-1",
        workspace_id=ws.id,
        created_by=creator.id,
        title="Draft Infographic",
        input_type="TEXT",
        status="PENDING_REVIEW",
    )
    await sub.insert()

    rev = SubmissionRevision(id="rev-rej-1", submission_id=sub.id, revision_number=1, content_hash="hash-rej", created_by=creator.id)
    await rev.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Rejection requires notes
        bad_resp = await client.post(
            f"/api/v1/submissions/{sub.id}/reject",
            headers=auth_headers_factory(reviewer),
            json={"decision_notes": ""},
        )
        assert bad_resp.status_code == 422

        # Valid rejection
        good_resp = await client.post(
            f"/api/v1/submissions/{sub.id}/reject",
            headers=auth_headers_factory(reviewer),
            json={"decision_notes": "Color contrast fails WCAG AA on slide 3. Please revise."},
        )
        assert good_resp.status_code == 200
        assert good_resp.json()["decision"] == "REJECTED"

        updated_sub = await Submission.get(sub.id)
        assert updated_sub.status == "NEEDS_CHANGES"


@pytest.mark.asyncio
async def test_public_certificate_verification():
    """Test public endpoint verifies cryptographic SHA-256 certificate authenticity."""
    ws, creator, reviewer, _ = await create_workspace_and_users()

    sub = Submission(id="sub-cert-verify", workspace_id=ws.id, created_by=creator.id, title="Audited Whitepaper", input_type="TEXT")
    await sub.insert()

    rev = SubmissionRevision(
        id="rev-cert-verify",
        submission_id=sub.id,
        revision_number=1,
        content_hash="whitepaper-hash-999",
        created_by=creator.id,
    )
    await rev.insert()

    appr = Approval(
        id="appr-cert-verify",
        submission_id=sub.id,
        revision_id=rev.id,
        decided_by=reviewer.id,
        decision="APPROVED",
        readiness_score_at_approval=92,
    )
    await appr.insert()

    cert_number = "VBT-CERT-ACME-TEST1234"
    now_iso = datetime.now(timezone.utc).isoformat()
    cert_payload = {
        "certificate_number": cert_number,
        "submission_id": sub.id,
        "revision_id": rev.id,
        "revision_hash": rev.content_hash,
        "workspace_id": ws.id,
        "approval_id": appr.id,
        "decided_by": reviewer.id,
        "readiness_score": 92,
        "issued_at": now_iso,
    }
    cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()

    cert = ComplianceCertificate(
        id="cert-verify-id",
        approval_id=appr.id,
        submission_id=sub.id,
        workspace_id=ws.id,
        certificate_number=cert_number,
        certificate_hash=cert_hash,
        issued_at=datetime.fromisoformat(now_iso),
        metadata_json={
            "submission_title": sub.title,
            "workspace_name": ws.name,
            "revision_content_hash": rev.content_hash,
            "approver_email": reviewer.email,
            "issued_at_iso": now_iso,
        },
    )
    await cert.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/certificates/{cert_number}/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["tamper_evident_verified"] is True
        assert data["certificate_number"] == cert_number
        assert data["certificate_hash"] == cert_hash
        assert data["submission_title"] == "Audited Whitepaper"
        assert data["decided_by_email"] == reviewer.email


@pytest.mark.asyncio
async def test_governance_insights_endpoint(auth_headers_factory):
    """Test governance analytics calculates aggregates, rates, and recurring violations."""
    ws, creator, reviewer, admin = await create_workspace_and_users()

    sub1 = Submission(id="sub-gov-1", workspace_id=ws.id, created_by=creator.id, title="Sub 1", input_type="TEXT", status="APPROVED")
    sub2 = Submission(id="sub-gov-2", workspace_id=ws.id, created_by=creator.id, title="Sub 2", input_type="TEXT", status="NEEDS_CHANGES")
    await sub1.insert()
    await sub2.insert()

    audit1 = AuditRun(id="audit-gov-1", submission_id=sub1.id, revision_id="rev-1", readiness_score=90)
    audit2 = AuditRun(id="audit-gov-2", submission_id=sub2.id, revision_id="rev-2", readiness_score=70)
    await audit1.insert()
    await audit2.insert()

    f1 = Finding(
        id="f-gov-1",
        audit_run_id=audit1.id,
        category="TERMINOLOGY",
        severity="MEDIUM",
        source_engine="DETERMINISTIC",
        title="Banned Term: synergy",
        description="",
    )
    f2 = Finding(
        id="f-gov-2",
        audit_run_id=audit2.id,
        category="TERMINOLOGY",
        severity="HIGH",
        source_engine="DETERMINISTIC",
        title="Banned Term: synergy",
        description="",
    )
    await f1.insert()
    await f2.insert()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/workspaces/{ws.id}/governance/insights",
            headers=auth_headers_factory(admin),
        )
        assert resp.status_code == 200
        insights = resp.json()
        assert insights["total_submissions"] == 2
        assert insights["total_approved"] == 1
        assert insights["total_rejected"] == 1
        assert insights["approval_rate"] == 50.0
        assert insights["avg_readiness_score"] == 80.0
        assert insights["category_breakdown"]["TERMINOLOGY"] == 2
        assert insights["top_violated_rules"][0]["rule_title"] == "Banned Term: synergy"
        assert insights["top_violated_rules"][0]["count"] == 2
