"""Comprehensive automated test suite for Checkpoint 8: Explainable Diff Workspace.

Verifies:
1. Diff engine granular token/word chunking and whitespace preservation.
2. Synchronized line-level diff calculations with insertion, deletion, and modification stats.
3. Full API endpoint for side-by-side diff between submission revisions (GET /submissions/{id}/diff).
4. Interactive suggestion acceptance creating an immutable incremental revision (v2) and chaining audit events.
5. Human-in-the-loop exception requests with recorded justification and finding status tracking.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.documents import (
    User,
    Workspace,
    Membership,
    Submission,
    SubmissionRevision,
    TerminologyRule,
    ApprovedFact,
    AuditRun,
    Finding,
    AuditEvent,
    ExceptionRequest,
)
from app.core.security import get_password_hash, create_access_token
from app.services.diff_engine import diff_engine


# --- 1. Unit Tests: Diff Engine ---

@pytest.mark.asyncio
async def test_diff_engine_word_chunks():
    """Verifies that diff_engine accurately flags deleted and inserted tokens."""
    orig = "Our platform offers unbreakable security for all clients."
    rev = "Our platform offers highly resilient security for all clients."

    chunks = diff_engine.compute_word_chunks(orig, rev)
    assert len(chunks) >= 3

    types = [c.type for c in chunks]
    assert "delete" in types
    assert "insert" in types

    deleted_text = "".join(c.text for c in chunks if c.type == "delete")
    inserted_text = "".join(c.text for c in chunks if c.type == "insert")

    assert "unbreakable" in deleted_text
    assert "highly resilient" in inserted_text


@pytest.mark.asyncio
async def test_diff_engine_line_matching():
    """Verifies side-by-side line indexing and modification counters."""
    orig = "Title: Overview\nLine 1: 99.99% uptime\nLine 2: Static text"
    rev = "Title: Overview\nLine 1: 99.9% uptime SLA\nLine 2: Static text\nLine 3: New footer"

    lines, stats = diff_engine.compute_line_diff(orig, rev)

    assert stats["unchanged"] >= 2
    assert stats["modifications"] >= 1 or stats["additions"] >= 1
    assert any(line.type == "equal" for line in lines)
    assert any(line.line_number_rev is not None for line in lines)


# --- 2. Integration Tests: API Endpoints ---

@pytest.mark.asyncio
async def test_api_get_submission_diff():
    """Verifies GET /submissions/{id}/diff comparing two content revisions."""
    user = User(email="author.diff@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user.insert()
    ws = Workspace(name="Diff WS", slug="diff-ws")
    await ws.insert()
    await Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR").insert()

    sub = Submission(
        workspace_id=ws.id,
        created_by=user.id,
        title="Q4 Marketing Deck",
        input_type="TEXT",
        status="DRAFT",
    )
    await sub.insert()

    # Revision 1
    rev1 = SubmissionRevision(
        submission_id=sub.id,
        revision_number=1,
        content_hash="hash_rev1",
        extracted_text="We guarantee 99.99% uptime with unbreakable cloud storage.",
        created_by=user.id,
    )
    await rev1.insert()

    # Revision 2
    rev2 = SubmissionRevision(
        submission_id=sub.id,
        revision_number=2,
        content_hash="hash_rev2",
        extracted_text="We guarantee 99.9% uptime SLA with highly resilient cloud storage.",
        created_by=user.id,
    )
    await rev2.insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/submissions/{sub.id}/diff?from_rev=1&to_rev=2",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["submission_id"] == sub.id
        assert data["from_revision_number"] == 1
        assert data["to_revision_number"] == 2
        assert len(data["chunks"]) > 0
        assert len(data["lines"]) > 0
        assert "stats" in data


@pytest.mark.asyncio
async def test_api_apply_suggestion_creates_incremental_revision():
    """Verifies accepting a suggestion creates v2, resolves finding, and chains audit event."""
    user = User(email="creator.suggest@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user.insert()
    ws = Workspace(name="Suggest WS", slug="suggest-ws")
    await ws.insert()
    await Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR").insert()

    sub = Submission(
        workspace_id=ws.id,
        created_by=user.id,
        title="Product Launch PR",
        input_type="TEXT",
        status="NEEDS_CHANGES",
    )
    await sub.insert()

    rev1 = SubmissionRevision(
        submission_id=sub.id,
        revision_number=1,
        content_hash="hash_rev1_sugg",
        extracted_text="Our platform offers unbreakable protection.",
        created_by=user.id,
    )
    await rev1.insert()

    audit_run = AuditRun(
        submission_id=sub.id,
        revision_id=rev1.id,
        status="COMPLETED",
        deterministic_status="COMPLETED",
        ai_status="PENDING",
        readiness_score=75,
    )
    await audit_run.insert()

    finding = Finding(
        audit_run_id=audit_run.id,
        category="TERMINOLOGY",
        severity="CRITICAL",
        source_engine="DETERMINISTIC",
        title="Banned terminology: 'unbreakable'",
        description="Term is prohibited",
        suggestion={
            "action": "REPLACE_TERM",
            "original": "unbreakable",
            "replacement": "highly resilient",
        },
        status="OPEN",
    )
    await finding.insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/submissions/{sub.id}/apply-suggestion",
            json={"finding_id": finding.id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert "v2" in data["message"]

        # Check that revision 2 exists
        rev2 = await SubmissionRevision.find_one(
            SubmissionRevision.submission_id == sub.id,
            SubmissionRevision.revision_number == 2,
        )
        assert rev2 is not None
        assert "highly resilient" in rev2.extracted_text
        assert "unbreakable" not in rev2.extracted_text

        # Check finding was resolved
        updated_f = await Finding.get(finding.id)
        assert updated_f.status == "RESOLVED"

        # Check AuditEvent chained
        event = await AuditEvent.find_one(
            AuditEvent.workspace_id == ws.id,
            AuditEvent.action == "SUGGESTION_APPLIED",
        )
        assert event is not None
        assert len(event.event_hash) == 64


@pytest.mark.asyncio
async def test_api_request_finding_exception():
    """Verifies submitting an exception request attaches justification and updates status."""
    user = User(email="creator.exc@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user.insert()
    ws = Workspace(name="Exception WS", slug="exc-ws")
    await ws.insert()
    await Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR").insert()

    sub = Submission(
        workspace_id=ws.id,
        created_by=user.id,
        title="Financial Report",
        input_type="TEXT",
        status="NEEDS_CHANGES",
    )
    await sub.insert()

    rev1 = SubmissionRevision(
        submission_id=sub.id,
        revision_number=1,
        content_hash="hash_rev1_exc",
        extracted_text="Special legacy contract requires distinct phrasing.",
        created_by=user.id,
    )
    await rev1.insert()

    audit_run = AuditRun(
        submission_id=sub.id,
        revision_id=rev1.id,
        status="COMPLETED",
        deterministic_status="COMPLETED",
        ai_status="PENDING",
        readiness_score=75,
    )
    await audit_run.insert()

    finding = Finding(
        audit_run_id=audit_run.id,
        category="TERMINOLOGY",
        severity="HIGH",
        source_engine="DETERMINISTIC",
        title="Off-brand phrasing detected",
        description="Phrasing deviates from brand standard",
        status="OPEN",
    )
    await finding.insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/findings/{finding.id}/exceptions",
            json={"reason": "Customer legal team specifically required legacy wording in clause 4.2."},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["finding_id"] == finding.id
        assert data["status"] == "PENDING"
        assert "legal team" in data["reason"]

        # Check Finding status was updated to EXCEPTION_REQUESTED
        updated_f = await Finding.get(finding.id)
        assert updated_f.status == "EXCEPTION_REQUESTED"

        # Check AuditEvent chained
        event = await AuditEvent.find_one(
            AuditEvent.workspace_id == ws.id,
            AuditEvent.action == "EXCEPTION_REQUESTED",
        )
        assert event is not None
        assert len(event.event_hash) == 64

        # Check GET /submissions/{id}/exceptions
        list_resp = await client.get(
            f"/api/v1/submissions/{sub.id}/exceptions",
            headers=headers,
        )
        assert list_resp.status_code == 200
        exceptions_list = list_resp.json()
        assert len(exceptions_list) == 1
        assert exceptions_list[0]["finding_id"] == finding.id
