"""Automated tests for Checkpoint 10: Compliance Certificate PDF export,
QR code verification proof, and download endpoints.
"""

import io
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
import pypdf

from app.main import app
from app.services.certificate_generator import generate_compliance_certificate_pdf
from app.models.documents import (
    User,
    Workspace,
    Membership,
    Submission,
    SubmissionRevision,
    Approval,
    ComplianceCertificate,
)
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_certificate_pdf_generator_structure():
    """Verify raw PDF generation generates valid binary PDF with embedded vector art and QR."""
    pdf_bytes = generate_compliance_certificate_pdf(
        certificate_number="VBT-CERT-TEST-9999",
        certificate_hash="a" * 64,
        submission_title="Automated Test Campaign Launch Copy",
        workspace_name="Acme Testing Workspace",
        readiness_score=96,
        approver_name="Senior Test Reviewer",
        approver_email="reviewer@test.com",
        issued_at=datetime.now(timezone.utc),
        verification_url="https://veribrand-trace.vercel.app/verify/VBT-CERT-TEST-9999",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 4000
    assert pdf_bytes.startswith(b"%PDF-")

    # Parse with PyPDF to confirm structural validity
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    text = page.extract_text()
    assert "OFFICIAL CERTIFICATE OF BRAND COMPLIANCE" in text
    assert "VBT-CERT-TEST-9999" in text
    assert "Acme Testing Workspace" in text
    assert "96%" in text
    assert "Suggest, Never Override" in text


@pytest.mark.asyncio
async def test_download_certificate_endpoint_success():
    """Verify GET /api/v1/certificates/{cert_number}/download returns downloadable PDF."""
    # 1. Setup workspace & accounts
    workspace = Workspace(name="Global Brand Studio", slug="global-studio", status="ACTIVE")
    await workspace.insert()

    creator = User(
        email="creator_cert@brand.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Creator User",
    )
    await creator.insert()

    reviewer = User(
        email="reviewer_cert@brand.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Authorized Brand Reviewer",
    )
    await reviewer.insert()

    # 2. Submission & Revision
    content_text = "Clean campaign copy with zero brand violations."
    submission = Submission(
        workspace_id=workspace.id,
        created_by=creator.id,
        title="Spring 2026 Brand Campaign",
        input_type="TEXT",
        status="APPROVED",
    )
    await submission.insert()

    rev = SubmissionRevision(
        submission_id=submission.id,
        revision_number=1,
        content=content_text,
        content_hash="abc123hash",
        created_by=creator.id,
    )
    await rev.insert()

    # 3. Approval & Certificate
    now = datetime.now(timezone.utc)
    approval = Approval(
        submission_id=submission.id,
        revision_id=rev.id,
        decided_by=reviewer.id,
        decision="APPROVED",
        decision_notes="All brand guidelines satisfied.",
        readiness_score_at_approval=95,
        created_at=now,
    )
    await approval.insert()

    cert_number = "VBT-CERT-202611-TEST01"
    cert_hash = "f" * 64
    cert = ComplianceCertificate(
        approval_id=approval.id,
        submission_id=submission.id,
        workspace_id=workspace.id,
        certificate_number=cert_number,
        certificate_hash=cert_hash,
        issued_at=now,
        metadata_json={
            "issued_at_iso": now.isoformat(),
            "revision_content_hash": rev.content_hash,
        },
    )
    await cert.insert()

    # 4. Request PDF download via ASGI Transport
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/certificates/{cert_number}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert f'attachment; filename="VeriBrand_Certificate_{cert_number}.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")

    # Verify extracted text contains key parameters
    reader = pypdf.PdfReader(io.BytesIO(response.content))
    extracted = reader.pages[0].extract_text()
    assert cert_number in extracted
    assert "Spring 2026 Brand Campaign" in extracted
    assert "95%" in extracted


@pytest.mark.asyncio
async def test_download_certificate_endpoint_not_found():
    """Verify downloading a non-existent certificate returns HTTP 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/certificates/NONEXISTENT-CERT-404/download")

    assert response.status_code == 404
    data = response.json()
    assert "does not exist or has been revoked" in data["detail"]
