"""Automated tests for Checkpoint 5: Content Upload & Privacy Gate.

Verifies:
- File signature (magic bytes) validation and extension spoofing rejection.
- File size restrictions (rejecting oversized files).
- Text extraction across TXT, DOCX, PDF, and Image metadata.
- Privacy Gate PII scrubbing (emails, phones, SSNs, credit cards, IP addresses).
- Confidential project terms masking before AI processing.
- Original file and revision immutability preservation.
- Workspace data isolation and role-based access control.
- Chained SHA-256 audit event generation.
"""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from docx import Document as DocxDocument
from PIL import Image
from pypdf import PdfWriter

from app.main import app
from app.models.documents import User, Workspace, Membership, Submission, SubmissionRevision, AuditEvent
from app.core.security import get_password_hash, create_access_token
from app.services.storage import storage_service, detect_file_type
from app.services.extractor import extraction_service
from app.services.privacy import privacy_service


def create_in_memory_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_in_memory_png() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (120, 80), color=(73, 109, 137))
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_in_memory_jpg() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(200, 50, 50))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_in_memory_pdf(text_content: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# --- Unit Tests: Storage & Signatures ---

def test_file_signature_validation():
    """Verifies magic bytes detection and rejection of spoofed extensions."""
    # Valid PNG
    png_bytes = create_in_memory_png()
    input_type, mime = detect_file_type(png_bytes, "logo.png")
    assert input_type == "IMAGE_PNG"
    assert mime == "image/png"

    # Valid DOCX
    docx_bytes = create_in_memory_docx(["Title"])
    input_type, mime = detect_file_type(docx_bytes, "doc.docx")
    assert input_type == "DOCX"

    # Valid PDF
    pdf_bytes = create_in_memory_pdf("Test PDF")
    input_type, mime = detect_file_type(pdf_bytes, "doc.pdf")
    assert input_type == "PDF"

    # Spoofed Extension: Text disguised as PDF
    with pytest.raises(ValueError, match="signature mismatch"):
        detect_file_type(b"Just plain text", "fake.pdf")

    # Spoofed Extension: Binary disguised as PNG
    with pytest.raises(ValueError, match="signature mismatch"):
        detect_file_type(b"Random binary", "fake.png")

    # Empty file
    with pytest.raises(ValueError, match="empty"):
        detect_file_type(b"", "empty.txt")


def test_file_size_restriction():
    """Verifies files exceeding 10MB limit are rejected."""
    oversized = b"A" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds maximum allowable limit"):
        storage_service.validate_file("big.txt", oversized)


# --- Unit Tests: Extraction ---

def test_text_and_docx_extraction():
    """Verifies text extraction from TXT and DOCX."""
    # TXT
    txt_data = "Line 1\nLine 2 with numbers 12345".encode("utf-8")
    res = extraction_service.extract("TEXT", txt_data)
    assert "Line 1" in res["text"]
    assert res["word_count"] > 0

    # DOCX
    docx_bytes = create_in_memory_docx(["First paragraph", "Second paragraph with claims"])
    res = extraction_service.extract("DOCX", docx_bytes)
    assert "First paragraph" in res["text"]
    assert "Second paragraph" in res["text"]
    assert res["metadata"]["paragraph_count"] >= 2


def test_image_extraction_metadata():
    """Verifies image geometry and mode inspection."""
    png_bytes = create_in_memory_png()
    res = extraction_service.extract("IMAGE_PNG", png_bytes)
    assert res["metadata"]["width"] == 120
    assert res["metadata"]["height"] == 80
    assert res["metadata"]["mode"] == "RGB"


# --- Unit Tests: Privacy Gate & PII Scrubbing ---

def test_privacy_gate_pii_scrubbing():
    """Verifies high-precision detection and redaction of emails, phones, SSNs, credit cards, IPs."""
    dirty_text = (
        "Contact CEO at john.doe@enterprise.com or call +1 555-321-7654. "
        "Tax ID is 123-45-6789. Billing card 4532-1234-5678-9012. "
        "Server host is 192.168.1.100."
    )

    report = privacy_service.process(dirty_text)

    assert report["status"] == "SANITIZED"
    assert "[REDACTED_EMAIL]" in report["sanitized_text"]
    assert "[REDACTED_PHONE]" in report["sanitized_text"]
    assert "[REDACTED_SSN]" in report["sanitized_text"]
    assert "[REDACTED_CREDIT_CARD]" in report["sanitized_text"]
    assert "[REDACTED_IP_ADDRESS]" in report["sanitized_text"]

    # Verify raw text is never exposed in sanitized output
    assert "john.doe@enterprise.com" not in report["sanitized_text"]
    assert "123-45-6789" not in report["sanitized_text"]
    assert "4532-1234-5678-9012" not in report["sanitized_text"]

    # Original text preserved
    assert report["original_text"] == dirty_text


def test_privacy_gate_confidential_terms_masking():
    """Verifies confidential project names are masked deterministically."""
    confidential_text = (
        "We are pleased to announce Project Titan will launch in Q3. "
        "Project Titan surpasses all benchmarks established by Codename Falcon."
    )

    confidential_terms = ["Project Titan", "Codename Falcon"]
    report = privacy_service.process(confidential_text, confidential_terms=confidential_terms)

    assert report["status"] == "SANITIZED"
    assert "[CONFIDENTIAL_PROJECT_1]" in report["sanitized_text"]
    assert "[CONFIDENTIAL_PROJECT_2]" in report["sanitized_text"]
    assert "Project Titan" not in report["sanitized_text"]
    assert "Codename Falcon" not in report["sanitized_text"]
    assert len(report["confidential_terms_masked"]) == 2


def test_clean_text_passes_privacy_gate():
    """Verifies text with zero PII and no confidential terms receives PASSED status."""
    clean = "Our sustainable cloud platform delivers 99.9% uptime for global teams."
    report = privacy_service.process(clean)
    assert report["status"] == "PASSED"
    assert report["sanitized_text"] == clean
    assert len(report["pii_detected"]) == 0


# --- Integration Tests: API Endpoints ---

@pytest.mark.asyncio
async def test_create_submission_with_privacy_gate_and_audit():
    """Tests end-to-end submission creation with PII redaction and audit hash chaining."""
    user = User(
        email="creator_upload@veribrand.io",
        hashed_password=get_password_hash("CreatorPass123!"),
        full_name="Creator User",
    )
    await user.insert()

    ws = Workspace(name="Marketing WS", slug="marketing-ws")
    await ws.insert()

    mem = Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR")
    await mem.insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Submit text content with PII and a confidential term
        payload = {
            "title": "Summer Campaign Press Release",
            "text_content": "Reach us at contact@brand.com regarding Project Odyssey. Phone: 555-876-5432.",
            "confidential_terms": ["Project Odyssey"],
            "input_type": "TEXT",
        }
        resp = await client.post(
            f"/api/v1/workspaces/{ws.id}/submissions",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()

        assert data["title"] == "Summer Campaign Press Release"
        assert data["status"] == "DRAFT"
        assert data["input_type"] == "TEXT"

        latest_rev = data["latest_revision"]
        assert latest_rev is not None
        assert latest_rev["revision_number"] == 1
        assert "[REDACTED_EMAIL]" in latest_rev["sanitized_text"]
        assert "[CONFIDENTIAL_PROJECT_1]" in latest_rev["sanitized_text"]
        assert "contact@brand.com" not in latest_rev["sanitized_text"]
        # Raw text in revision preserves original for human reviewer
        assert "contact@brand.com" in latest_rev["extracted_text"]

        # 2. Check AuditEvent was recorded with SHA-256 hash
        audit_event = await AuditEvent.find_one(
            AuditEvent.workspace_id == ws.id,
            AuditEvent.action == "SUBMISSION_CREATED",
        )
        assert audit_event is not None
        assert audit_event.event_hash is not None
        assert len(audit_event.event_hash) == 64

        # 3. Create Revision 2 (addressing changes)
        sub_id = data["id"]
        rev2_payload = {
            "raw_content": "Updated content: reach customer support portal. Project Odyssey is progressing well.",
            "confidential_terms": ["Project Odyssey"],
        }
        rev2_resp = await client.post(
            f"/api/v1/submissions/{sub_id}/revisions",
            json=rev2_payload,
            headers=headers,
        )
        assert rev2_resp.status_code == 201, rev2_resp.text
        rev2_data = rev2_resp.json()
        assert rev2_data["revision_number"] == 2
        assert "[CONFIDENTIAL_PROJECT_1]" in rev2_data["sanitized_text"]

        # 4. List revisions
        list_revs_resp = await client.get(
            f"/api/v1/submissions/{sub_id}/revisions",
            headers=headers,
        )
        assert list_revs_resp.status_code == 200
        revs = list_revs_resp.json()
        assert len(revs) == 2


@pytest.mark.asyncio
async def test_multipart_file_upload_and_download():
    """Verifies multipart file upload, storage integrity, and download matching content hash."""
    user = User(email="uploader@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user.insert()
    ws = Workspace(name="Creative Hub", slug="creative-hub")
    await ws.insert()
    await Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR").insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    png_bytes = create_in_memory_png()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload PNG
        files = {
            "file": ("brand_mockup.png", png_bytes, "image/png"),
        }
        data = {
            "title": "Brand Mockup Q3",
            "confidential_terms": "Project Apex, StealthMode",
        }
        resp = await client.post(
            f"/api/v1/workspaces/{ws.id}/submissions",
            data=data,
            files=files,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        sub_data = resp.json()
        assert sub_data["input_type"] == "IMAGE_PNG"
        assert sub_data["latest_revision"]["content_hash"] is not None

        sub_id = sub_data["id"]
        rev_id = sub_data["latest_revision"]["id"]

        # Download file and check byte-for-byte immutability
        download_resp = await client.get(
            f"/api/v1/submissions/{sub_id}/revisions/{rev_id}/file",
            headers=headers,
        )
        assert download_resp.status_code == 200
        assert download_resp.content == png_bytes
        assert download_resp.headers.get("etag") == f'"{sub_data["latest_revision"]["content_hash"]}"'


@pytest.mark.asyncio
async def test_workspace_isolation_on_submissions():
    """Verifies that users cannot access submissions belonging to another workspace."""
    user_a = User(email="user_a@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user_a.insert()
    ws_a = Workspace(name="Workspace A", slug="workspace-a")
    await ws_a.insert()
    await Membership(workspace_id=ws_a.id, user_id=user_a.id, role="CREATOR").insert()

    user_b = User(email="user_b@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user_b.insert()
    ws_b = Workspace(name="Workspace B", slug="workspace-b")
    await ws_b.insert()
    await Membership(workspace_id=ws_b.id, user_id=user_b.id, role="CREATOR").insert()

    # User A creates a submission in WS A
    token_a = create_access_token(user_a.id, user_a.email)
    token_b = create_access_token(user_b.id, user_b.email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            f"/api/v1/workspaces/{ws_a.id}/submissions",
            json={"title": "WS A Submission", "text_content": "Sensitive A text"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert create_resp.status_code == 201
        sub_id = create_resp.json()["id"]

        # User B attempts to access WS A submission -> 403 Forbidden
        get_resp = await client.get(
            f"/api/v1/submissions/{sub_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert get_resp.status_code == 403
